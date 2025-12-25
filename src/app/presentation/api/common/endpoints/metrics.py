from fastapi import APIRouter
from fastapi import Response
from prometheus_client import generate_latest


router = APIRouter()


@router.get("/metrics")
def get_metrics() -> Response:
    """
    Expose Prometheus metrics.
    """
    return Response(
        content=generate_latest(),
        media_type="text/plain",
    )
