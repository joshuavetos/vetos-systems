from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .core import ScalpelEngine

app = FastAPI(title="Text Scalpel API", version="3.0.0")

# Configure CORS to allow your React frontend to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your specific domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScalpelRequest(BaseModel):
    source_code: str
    anchor_text: str
    new_code: str
    position: str = "after"

@app.get("/health")
async def health_check():
    return {"status": "online", "version": "3.0.0"}

@app.post("/insert")
async def api_insert(req: ScalpelRequest):
    try:
        engine = ScalpelEngine()
        result = engine.insert(req.source_code, req.anchor_text, req.new_code, req.position)
        return {"status": "success", "code": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
