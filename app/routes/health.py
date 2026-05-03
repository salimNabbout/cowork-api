from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Verifica se a API está no ar."""
    return {"status": "ok"}
