from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class Citation(BaseModel):
    title: str
    source: str
    score: float


class PendingAction(BaseModel):
    id: str
    action_type: str
    summary: str
    status: str


class AskResponse(BaseModel):
    answer: str
    route: str
    citations: list[Citation]
    pending_action: PendingAction | None = None
    cached: bool = False


class HealthResponse(BaseModel):
    status: str
    document_count: int
    database: str
    cache: str


class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=10, max_length=10000)


class ActionDecisionResponse(BaseModel):
    id: str
    status: str
    ticket_id: int | None = None


class ActionItem(BaseModel):
    id: str
    action_type: str
    summary: str
    status: str
    created_at: str


class TicketItem(BaseModel):
    id: int
    title: str
    description: str
    status: str
    created_at: str


class DashboardMetrics(BaseModel):
    query_count: int
    pending_action_count: int
    ticket_count: int
    document_count: int

