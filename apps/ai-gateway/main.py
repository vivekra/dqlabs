import os
import httpx
import logging
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("digitalq-ai-gateway")

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    OLLAMA_URL: str = "http://ollama:11434"
    OPENAI_API_KEY: str = "mock_key_for_dev"
    AI_MODE: str = "hybrid" # hybrid, openai_only, ollama_only

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

app = FastAPI(
    title="DigitalQ Labs AI Gateway",
    description="Intelligent routing gateway supporting hybrid OpenAI and local Ollama model fallback executions.",
    version="1.0.0",
)

class DiagnosticRequest(BaseModel):
    query: str
    error_logs: str | None = None
    kubernetes_events: str | None = None
    lab_runbook: str | None = None

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {
        "status": "healthy",
        "ai_mode": settings.AI_MODE,
        "ollama_connected": await check_ollama_status(),
    }

async def check_ollama_status() -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.OLLAMA_URL}/api/tags", timeout=2.0)
            return response.status_code == 200
    except Exception:
        return False

@app.post("/api/v1/ai/diagnose", status_code=status.HTTP_200_OK)
async def diagnose_incident(req: DiagnosticRequest):
    """Processes troubleshooting request via smart hybrid models selector."""
    logger.info(f"AI diagnosing request for query: {req.query}")
    
    # Simple Local / Mock triage response
    is_complex = req.error_logs is not None and len(req.error_logs) > 500
    
    if settings.AI_MODE == "openai_only" or (settings.AI_MODE == "hybrid" and is_complex):
        # In a real environment, route payload to OpenAI completion endpoints
        return {
            "source": "openai",
            "model": "gpt-4o-mini",
            "diagnosis": "CrashLoopBackOff identified. The container is crashing because the entrypoint script cannot locate configuration variables. Check your configmaps.",
            "correction_command": "kubectl get configmaps -n tenant-devops-bootcamp",
        }
    else:
        # Fallback to local Ollama execution mock
        return {
            "source": "ollama",
            "model": "llama3",
            "diagnosis": "Pod log shows service listening successfully. This error is likely an incorrect readinessProbe path configured in deployment.yaml.",
            "correction_command": "kubectl describe pod -n tenant-devops-bootcamp",
        }
