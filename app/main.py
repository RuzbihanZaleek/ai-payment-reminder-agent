from fastapi import FastAPI

app = FastAPI(
    title="AI Payment Reminder Agent"
)

@app.get("/")
def health():
    return {
        "status": "running"
    }