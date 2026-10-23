import os
from dotenv import load_dotenv

load_dotenv()

def env(key, default=None):
    return os.getenv(key, default)

class Config:
    PORT = int(env("APP_PORT", "8000"))
    AUTH0_DOMAIN = env("AUTH0_DOMAIN", "")
    AUTH0_CLIENT_ID = env("AUTH0_CLIENT_ID", "")
    AUTH0_CLIENT_SECRET = env("AUTH0_CLIENT_SECRET", "")
    AUTH0_AUDIENCE = env("AUTH0_AUDIENCE", "https://intentlock-api")
    AUTH0_ALGORITHMS = [a.strip() for a in env("AUTH0_ALGORITHMS", "RS256").split(",")]
    TOKEN_VAULT_CONNECTION = env("TOKEN_VAULT_CONNECTION", "google-oauth2")
    GMAIL_SCOPES = [s.strip() for s in env("GMAIL_SCOPES", "gmail.read,gmail.compose").split(",")]
    FGA_API_URL = env("FGA_API_URL", "https://api.us1.fga.dev")
    FGA_STORE_ID = env("FGA_STORE_ID", "")
    FGA_MODEL_ID = env("FGA_MODEL_ID", "")
    FGA_CLIENT_ID = env("FGA_CLIENT_ID", "")
    FGA_CLIENT_SECRET = env("FGA_CLIENT_SECRET", "")
    FGA_API_TOKEN_ISSUER = env("FGA_API_TOKEN_ISSUER", "auth.fga.dev")
    FGA_API_AUDIENCE = env("FGA_API_AUDIENCE", "https://api.us1.fga.dev/")
    OLLAMA_URL = env("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = env("OLLAMA_MODEL", "gemma3:4b")
    OLLAMA_FALLBACK = env("OLLAMA_FALLBACK", "gemma2:2b-it")
    DATABASE_PATH = env("DATABASE_PATH", "./intentlock.db")
    MOCK_LLM = env("MOCK_LLM", "0") == "1"
    MOCK_CONNECTORS = env("MOCK_CONNECTORS", "0") == "1"

config = Config()
