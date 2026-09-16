from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.knowledge import KnowledgeBase
from app.llm import generate_grounded_answer


ROOT_DIR = Path(__file__).resolve().parents[1]
knowledge_base = KnowledgeBase(ROOT_DIR / "knowledge")


class WorkflowState(TypedDict):
    question: str
    matches: list[dict]
    answer: str
    route: str
    action_type: str


ACTION_TERMS = ("报修", "工单", "申请", "开通", "重置")
EXECUTION_TERMS = ("帮我", "请", "创建", "提交", "办理")


def classify_intent(state: WorkflowState) -> dict:
    question = state["question"]
    wants_action = any(term in question for term in ACTION_TERMS) and any(term in question for term in EXECUTION_TERMS)
    action_type = "create_support_ticket" if wants_action else ""
    return {"action_type": action_type}


def retrieve_knowledge(state: WorkflowState) -> dict:
    return {
        "matches": knowledge_base.search(state["question"]),
        "route": "action_preview" if state.get("action_type") else "knowledge_search",
    }


def compose_grounded_answer(state: WorkflowState) -> dict:
    matches = state.get("matches", [])
    if not matches:
        return {
            "answer": "知识库中暂时没有找到相关内容，建议转人工支持。",
        }

    best_match = matches[0]
    context = "\n\n".join(item["content"] for item in matches)
    generated = generate_grounded_answer(state["question"], context)
    if generated:
        return {"answer": generated}
    lines = [line.strip() for line in best_match["content"].splitlines()[1:] if line.strip()]
    summary = " ".join(lines[:4])
    suffix = " 系统已生成待确认的支持工单，确认后才会执行。" if state.get("action_type") else ""
    return {"answer": f"根据《{best_match['title']}》：{summary}{suffix}"}


builder = StateGraph(WorkflowState)
builder.add_node("classify", classify_intent)
builder.add_node("retrieve", retrieve_knowledge)
builder.add_node("compose", compose_grounded_answer)
builder.add_edge(START, "classify")
builder.add_edge("classify", "retrieve")
builder.add_edge("retrieve", "compose")
builder.add_edge("compose", END)
workflow = builder.compile()

