import httpx, json
from backend.app.config import config

class LLMClient:
    def __init__(self, model=None):
        self.model = model or config.OLLAMA_MODEL
        self.url = config.OLLAMA_URL

    async def generate(self, prompt: str, temperature: float = 0.0, json_mode: bool = True) -> str:
        if config.MOCK_LLM:
            return self._mock(prompt)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(f"{self.url}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            return data.get("response", "")

    def _mock(self, prompt: str) -> str:
        # minimal mock for tests/offline
        if "Extract the intent atoms" in prompt:
            # crude: wrap whole message as entity? return empty-ish
            return '{"atoms":[]}'
        if "style editor" in prompt:
            # echo original
            import re
            m = re.search(r"MESSAGE: (.*?)(?:\nReturn:|$)", prompt, re.S)
            orig = m.group(1).strip() if m else ""
            return json.dumps({"rewrite": orig, "changes": []})
        if "PRESERVED" in prompt or "For each contract atom" in prompt:
            return '{"verdicts":[]}'
        return "{}"

    async def try_models(self, prompt, temperature=0.0, json_mode=True):
        try:
            return await self.generate(prompt, temperature, json_mode)
        except Exception:
            # fallback
            self.model = config.OLLAMA_FALLBACK
            return await self.generate(prompt, temperature, json_mode)
