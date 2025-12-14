from fastapi import APIRouter

router = APIRouter()


@router.post("/answer/generate", tags=["rag"])
def generate_answer() -> dict[str, str]:
    return {}
