import httpx

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def generate_grounded_answer(question: str, context: str) -> str | None:
    """Use an OpenAI-compatible API when configured; otherwise keep the local fallback."""
    if not LLM_API_KEY:
        return None
    prompt = (
        "你是企业信息化知识助手。只能依据给定资料回答，并用简洁中文说明。"
        "如果资料不足，直接说明需要转人工，不得编造。\n\n"
        f"资料：\n{context}\n\n问题：{question}"
    )
    try:
        response = httpx.post(
            f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


