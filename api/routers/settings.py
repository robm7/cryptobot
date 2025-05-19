import logging
from fastapi import APIRouter, HTTPException, Body, status
from pydantic import BaseModel
from typing import Dict

from core.runtime_settings import RuntimeSettings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

class DryRunUpdateRequest(BaseModel):
    dry_run: bool

@router.put("/dry_run", response_model=Dict[str, bool])
async def update_dry_run_status(
    payload: DryRunUpdateRequest = Body(...)
):
    """
    Update the runtime DRY_RUN status.
    """
    try:
        previous_status = RuntimeSettings.get_dry_run_status()
        RuntimeSettings.set_dry_run_status(payload.dry_run)
        new_status = RuntimeSettings.get_dry_run_status()
        logger.info(f"DRY_RUN status changed from {previous_status} to {new_status} via API.")
        return {"dry_run": new_status}
    except Exception as e:
        logger.error(f"Error updating DRY_RUN status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update DRY_RUN status"
        )

@router.get("/dry_run", response_model=Dict[str, bool])
async def get_dry_run_status_endpoint():
    """
    Get the current runtime DRY_RUN status.
    """
    try:
        current_status = RuntimeSettings.get_dry_run_status()
        return {"dry_run": current_status}
    except Exception as e:
        logger.error(f"Error retrieving DRY_RUN status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve DRY_RUN status"
        )