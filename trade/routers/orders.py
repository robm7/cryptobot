from fastapi import APIRouter
from pydantic import BaseModel

class OrderRequest(BaseModel):
    exchange: str
    symbol: str
    side: str
    amount: float
    type: str
    client_order_id: str | None = None

router = APIRouter()

@router.post("/")
async def create_order(order: OrderRequest):
    return {"status": "dry_run", "order": order.dict()}