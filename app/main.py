import json
import re
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.cache import answer_cache
from app.config import DATABASE_URL, ROOT_DIR
from app.db import ActionRecord, QueryRecord, SessionLocal, TicketRecord, dashboard_metrics, init_db
from app.graph import knowledge_base, workflow
from app.schemas import (
    ActionDecisionResponse,
    ActionItem,
    AskRequest,
    AskResponse,
    DashboardMetrics,
    HealthResponse,
    KnowledgeCreate,
    TicketItem,
)


app = FastAPI(
    title="企业知识与流程协同平台",
    version="1.0.0",
    description="知识检索、来源引用、工单审批与执行审计一体化演示平台。",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
init_db()


def serialize_result(result: dict, *, cached: bool = False) -> dict:
    return {
        "answer": result["answer"],
        "route": result["route"],
        "citations": [
            {"title": item["title"], "source": item["source"], "score": item["score"]}
            for item in result.get("matches", [])
        ],
        "pending_action": None,
        "cached": cached,
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        document_count=len(knowledge_base.documents),
        database="mysql" if DATABASE_URL.startswith("mysql") else "sqlite",
        cache=answer_cache.status(),
    )


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    cached = answer_cache.get(request.question)
    if cached:
        cached["cached"] = True
        with SessionLocal() as session:
            session.add(QueryRecord(question=request.question, route=cached["route"], answer=cached["answer"], cached=1))
            session.commit()
        return AskResponse(**cached)

    result = workflow.invoke(
        {"question": request.question, "matches": [], "answer": "", "route": "", "action_type": ""}
    )
    payload = serialize_result(result)
    with SessionLocal() as session:
        if result.get("action_type"):
            action = ActionRecord(
                action_type=result["action_type"],
                summary=f"为问题“{request.question[:80]}”创建 IT 支持工单",
                payload_json=json.dumps({"question": request.question}, ensure_ascii=False),
            )
            session.add(action)
            session.flush()
            payload["pending_action"] = {
                "id": action.id,
                "action_type": action.action_type,
                "summary": action.summary,
                "status": action.status,
            }
        session.add(QueryRecord(question=request.question, route=result["route"], answer=result["answer"]))
        session.commit()
    if not result.get("action_type"):
        answer_cache.set(request.question, payload)
    return AskResponse(**payload)


@app.get("/api/knowledge")
def list_knowledge() -> list[dict]:
    return [
        {"title": item.title, "source": item.source, "preview": item.content[:160]}
        for item in knowledge_base.documents
    ]


@app.post("/api/knowledge")
def create_knowledge(item: KnowledgeCreate) -> dict:
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", item.title).strip("-").lower()
    if not safe_name:
        safe_name = f"document-{len(knowledge_base.documents) + 1}"
    path = ROOT_DIR / "knowledge" / f"{safe_name}.md"
    suffix = 2
    while path.exists():
        path = ROOT_DIR / "knowledge" / f"{safe_name}-{suffix}.md"
        suffix += 1
    path.write_text(f"# {item.title}\n\n{item.content.strip()}\n", encoding="utf-8")
    return {"source": path.name, "document_count": knowledge_base.reindex()}


@app.post("/api/knowledge/reindex")
def reindex() -> dict:
    return {"document_count": knowledge_base.reindex()}


@app.get("/api/actions", response_model=list[ActionItem])
def list_actions() -> list[ActionItem]:
    with SessionLocal() as session:
        rows = session.query(ActionRecord).order_by(ActionRecord.created_at.desc()).limit(50).all()
        return [
            ActionItem(
                id=row.id,
                action_type=row.action_type,
                summary=row.summary,
                status=row.status,
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        ]


@app.post("/api/actions/{action_id}/approve", response_model=ActionDecisionResponse)
def approve_action(action_id: str) -> ActionDecisionResponse:
    with SessionLocal() as session:
        action = session.get(ActionRecord, action_id)
        if not action:
            raise HTTPException(status_code=404, detail="操作不存在")
        if action.status != "pending":
            raise HTTPException(status_code=409, detail="操作已经处理")
        ticket = TicketRecord(
            title="IT 支持工单",
            description=action.payload.get("question", action.summary),
            source_action_id=action.id,
        )
        action.status = "approved"
        action.decided_at = datetime.now(timezone.utc)
        session.add(ticket)
        session.commit()
        return ActionDecisionResponse(id=action.id, status=action.status, ticket_id=ticket.id)


@app.post("/api/actions/{action_id}/reject", response_model=ActionDecisionResponse)
def reject_action(action_id: str) -> ActionDecisionResponse:
    with SessionLocal() as session:
        action = session.get(ActionRecord, action_id)
        if not action:
            raise HTTPException(status_code=404, detail="操作不存在")
        if action.status != "pending":
            raise HTTPException(status_code=409, detail="操作已经处理")
        action.status = "rejected"
        action.decided_at = datetime.now(timezone.utc)
        session.commit()
        return ActionDecisionResponse(id=action.id, status=action.status)


@app.get("/api/tickets", response_model=list[TicketItem])
def list_tickets() -> list[TicketItem]:
    with SessionLocal() as session:
        rows = session.query(TicketRecord).order_by(TicketRecord.created_at.desc()).limit(50).all()
        return [
            TicketItem(
                id=row.id,
                title=row.title,
                description=row.description,
                status=row.status,
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        ]


@app.get("/api/dashboard", response_model=DashboardMetrics)
def dashboard() -> DashboardMetrics:
    return DashboardMetrics(**dashboard_metrics(), document_count=len(knowledge_base.documents))


FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")


