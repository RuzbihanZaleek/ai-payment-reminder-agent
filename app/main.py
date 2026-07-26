from fastapi import FastAPI

from app.api.agent import router as agent_router

app = FastAPI(
    title="AI Payment Reminder Agent"
)

app.include_router(agent_router)


@app.get("/")
def health():
    return {
        "status": "running"
    }
