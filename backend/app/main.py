from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from backend.app.config import config
from backend.app import db
from backend.app.routes import drafts, inbox

app = FastAPI(title="IntentLock")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    db.init_db()

app.include_router(drafts.router)
app.include_router(inbox.router)

@app.get("/api/config")
def api_config():
    from backend.app.config import config
    return {
        "auth0_domain": config.AUTH0_DOMAIN,
        "auth0_client_id": config.AUTH0_CLIENT_ID,
        "auth0_audience": config.AUTH0_AUDIENCE,
        "mock_llm": config.MOCK_LLM,
        "mock_connectors": config.MOCK_CONNECTORS,
    }

# serve frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))
