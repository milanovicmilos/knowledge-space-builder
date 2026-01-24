from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SOTIS 2026 API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "SOTIS 2026 Knowledge Space API is Running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Placeholder for future endpoints
# from .endpoints import knowledge_space
# app.include_router(knowledge_space.router)
