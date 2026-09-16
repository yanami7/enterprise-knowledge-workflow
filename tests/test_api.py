from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_reports_indexed_documents() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["document_count"] >= 5


def test_password_question_returns_account_guide() -> None:
    response = client.post("/api/ask", json={"question": "密码忘记了怎么重置？"})
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "knowledge_search"
    assert body["citations"][0]["source"] == "account-password.md"


def test_unknown_question_falls_back_to_human_support() -> None:
    response = client.post("/api/ask", json={"question": "食堂今天有什么菜？"})
    assert response.status_code == 200
    assert "人工支持" in response.json()["answer"]


def test_ticket_action_requires_approval_before_execution() -> None:
    response = client.post("/api/ask", json={"question": "业务系统无法登录，请帮我创建支持工单"})
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "action_preview"
    assert body["pending_action"]["status"] == "pending"

    approved = client.post(f"/api/actions/{body['pending_action']['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["ticket_id"] > 0

