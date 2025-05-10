from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

from models.strategy import Strategy, StrategyVersion
from schemas.strategy import (
    StrategyCreate,
    StrategyUpdate,
    StrategyResponse,
    StrategyVersion as SchemaStrategyVersion
)
from database import get_db
from auth_middleware import get_current_user, has_role

from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(
    prefix="/strategies",
    tags=["strategies"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"}
    },
    dependencies=[Depends(oauth2_scheme)]
)
logger = logging.getLogger(__name__)

@router.get(
    "/",
    response_model=List[StrategyResponse],
    summary="List trading strategies",
    description="""Returns a list of all trading strategies.
    Can be filtered to show only active strategies.""",
    response_description="List of strategy objects",
    responses={
        200: {
            "description": "Successful operation",
            "content": {
                "application/json": {
                    "example": [{
                        "id": 1,
                        "name": "Mean Reversion",
                        "is_active": true,
                        "version": 2
                    }]
                }
            }
        },
        500: {"description": "Internal server error"}
    }
)
def list_strategies(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List all strategies, optionally filtered by active status
    
    - **active_only**: If True (default), returns only active strategies
    - **Returns**: List of strategy objects with basic info
    """
    try:
        query = db.query(Strategy)
        if active_only:
            query = query.filter(Strategy.is_active == True)
        
        strategies = query.all()
        logger.info(f"Listed {len(strategies)} strategies")
        return strategies
    except Exception as e:
        logger.error(f"Error listing strategies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving strategies"
        )

@router.get(
    "/{id}",
    response_model=StrategyResponse,
    summary="Get strategy details",
    description="Returns full details for a specific strategy including version history",
    responses={
        200: {
            "description": "Successful operation",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Mean Reversion",
                        "description": "Basic mean reversion strategy",
                        "parameters": {"lookback": 14, "threshold": 1.5},
                        "is_active": true,
                        "version": 2,
                        "versions": [
                            {"version": 1, "parameters": {"lookback": 10, "threshold": 1.0}},
                            {"version": 2, "parameters": {"lookback": 14, "threshold": 1.5}}
                        ]
                    }
                }
            }
        },
        404: {"description": "Strategy not found"},
        500: {"description": "Internal server error"}
    }
)
def get_strategy(
    id: int = Path(..., description="ID of strategy to retrieve", example=1),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a single strategy by ID with version history
    
    - **id**: The strategy ID to retrieve
    - **Returns**: Full strategy details including all versions
    - **Raises**:
        - HTTPException 404 if strategy not found
        - HTTPException 500 for server errors
    """
    try:
        strategy = db.query(Strategy).filter(Strategy.id == id).first()
        if not strategy:
            logger.warning(f"Strategy not found: {id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        # Get version history
        versions = db.query(StrategyVersion)\
            .filter(StrategyVersion.strategy_id == id)\
            .order_by(StrategyVersion.version.desc())\
            .all()
        
        strategy_response = StrategyResponse.from_orm(strategy)
        strategy_response.versions = [
            SchemaStrategyVersion.from_orm(v) for v in versions
        ]
        
        logger.info(f"Retrieved strategy: {id}")
        return strategy_response
    except Exception as e:
        logger.error(f"Error getting strategy {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving strategy"
        )

@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
def create_strategy(
    strategy: StrategyCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(has_role(["admin", "trader"]))
):
    """Create a new strategy"""
    try:
        db_strategy = Strategy(**strategy.dict())
        db.add(db_strategy)
        db.commit()
        db.refresh(db_strategy)
        
        # Create initial version
        version = StrategyVersion(
            strategy_id=db_strategy.id,
            version=db_strategy.version,
            parameters=db_strategy.parameters
        )
        db.add(version)
        db.commit()
        
        logger.info(f"Created strategy: {db_strategy.id}")
        return db_strategy
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating strategy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{id}", response_model=StrategyResponse)
def update_strategy(
    id: int,
    strategy: StrategyUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(has_role(["admin", "trader"]))
):
    """Update an existing strategy and create new version if parameters changed"""
    try:
        db_strategy = db.query(Strategy).filter(Strategy.id == id).first()
        if not db_strategy:
            logger.warning(f"Strategy not found for update: {id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        update_data = strategy.dict(exclude_unset=True)
        version_changed = False
        
        # Check if parameters changed
        if 'parameters' in update_data:
            if update_data['parameters'] != db_strategy.parameters:
                version_changed = True
                update_data['version'] = db_strategy.version + 1

        for field, value in update_data.items():
            setattr(db_strategy, field, value)

        db.commit()
        
        if version_changed:
            # Create new version
            version = StrategyVersion(
                strategy_id=db_strategy.id,
                version=db_strategy.version,
                parameters=db_strategy.parameters
            )
            db.add(version)
            db.commit()

        db.refresh(db_strategy)
        logger.info(f"Updated strategy: {id}")
        return db_strategy
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating strategy {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_strategy(
    id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(has_role(["admin"]))
):
    """Delete a strategy and its versions"""
    try:
        strategy = db.query(Strategy).filter(Strategy.id == id).first()
        if not strategy:
            logger.warning(f"Strategy not found for deletion: {id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        # Delete versions first
        db.query(StrategyVersion)\
            .filter(StrategyVersion.strategy_id == id)\
            .delete()
        
        db.delete(strategy)
        db.commit()
        logger.info(f"Deleted strategy: {id}")
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting strategy {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting strategy"
        )

@router.post("/{id}/activate", response_model=StrategyResponse)
def activate_strategy(
    id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(has_role(["admin", "trader"]))
):
    """Activate a strategy"""
    return _set_strategy_active_status(id, True, db)

@router.post("/{id}/deactivate", response_model=StrategyResponse)
def deactivate_strategy(
    id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(has_role(["admin", "trader"]))
):
    """Deactivate a strategy"""
    return _set_strategy_active_status(id, False, db)

def _set_strategy_active_status(
    id: int, 
    active: bool, 
    db: Session
) -> StrategyResponse:
    """Helper function to set strategy active status"""
    try:
        strategy = db.query(Strategy).filter(Strategy.id == id).first()
        if not strategy:
            logger.warning(f"Strategy not found for activation: {id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        strategy.is_active = active
        db.commit()
        db.refresh(strategy)
        
        action = "activated" if active else "deactivated"
        logger.info(f"{action.capitalize()} strategy: {id}")
        return strategy
    except Exception as e:
        db.rollback()
        logger.error(f"Error changing active status for strategy {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating strategy status"
        )

@router.get("/{id}/versions", response_model=List[SchemaStrategyVersion])
def get_strategy_versions(
    id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get version history for a strategy"""
    try:
        versions = db.query(StrategyVersion)\
            .filter(StrategyVersion.strategy_id == id)\
            .order_by(StrategyVersion.version.desc())\
            .all()
        
        if not versions:
            logger.warning(f"No versions found for strategy: {id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No versions found"
            )

        logger.info(f"Retrieved versions for strategy: {id}")
        return versions
    except Exception as e:
        logger.error(f"Error getting versions for strategy {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving versions"
        )