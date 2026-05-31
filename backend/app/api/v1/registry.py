import logging
from typing import List

from fastapi import APIRouter, HTTPException

from backend.app.schemas.registry import AssetConfig, LexiconConfig
from backend.app.services.registry import dynamic_registry

router = APIRouter()
logger = logging.getLogger("app")


@router.get("/assets", response_model=List[AssetConfig])
async def get_active_assets() -> List[AssetConfig]:
    """
    Returns the dynamic list of active assets available in the system.
    """
    try:
        return await dynamic_registry.get_active_assets()
    except Exception as exc:
        logger.error(f"Failed to fetch active assets: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/lexicon", response_model=LexiconConfig)
async def get_lexicon() -> LexiconConfig:
    """
    Returns the dynamically configured sentiment lexicon.
    """
    try:
        return await dynamic_registry.get_lexicon()
    except Exception as exc:
        logger.error(f"Failed to fetch lexicon: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")
