from fastapi import FastAPI

from app.api.agent import router as agent_router
from app.api.whatsapp import router as whatsapp_router

app = FastAPI(
    title="AI Payment Reminder Agent"
)

app.include_router(agent_router)
app.include_router(whatsapp_router)


@app.get("/")
def health():
    return {
        "status": "running"
    }
