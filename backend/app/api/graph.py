from fastapi import APIRouter, HTTPException

from app.services.graph.read_service import (
    get_case_network,
    get_entity,
)

router = APIRouter(tags=["Graph"])


@router.get("/cases/{case_id}/network")
def case_network(case_id: str):
    try:
        return get_case_network(case_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/entities/{entity_id}")
def entity_details(entity_id: str):
    try:
        result = get_entity(entity_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Entity not found",
            )

        return result

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))