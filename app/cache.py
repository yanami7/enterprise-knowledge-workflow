import json

from redis import Redis

from app.config import REDIS_URL


class AnswerCache:
    def __init__(self) -> None:
        self.client = Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=0.2)

    def get(self, key: str) -> dict | None:
        try:
            value = self.client.get(f"answer:{key.strip().lower()}")
            return json.loads(value) if value else None
        except Exception:
            return None

    def set(self, key: str, value: dict) -> None:
        try:
            self.client.setex(f"answer:{key.strip().lower()}", 300, json.dumps(value, ensure_ascii=False))
        except Exception:
            return

    def status(self) -> str:
        try:
            return "connected" if self.client.ping() else "unavailable"
        except Exception:
            return "fallback"


answer_cache = AnswerCache()


