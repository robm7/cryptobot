from fastapi import APIRouter, HTTPException
from typing import List
from .config import get_exchange_client
from .errors import ExchangeError

router = APIRouter()

class ExchangeRouter:
    def __init__(self):
        self._router = APIRouter()
        self._setup_routes()

    @property
    def router(self):
        return self._router

    def _setup_routes(self):
        self._router.add_api_route("/ticker/{exchange}/{pair}", self.get_ticker, methods=["GET"])
        self._router.add_api_route("/order", self.place_order, methods=["POST"])
        self._router.add_api_route("/order/{exchange}/{order_id}", self.cancel_order, methods=["DELETE"])
        self._router.add_api_route("/balance/{exchange}/{asset}", self.get_balance, methods=["GET"])

    async def get_ticker(self, exchange: str, pair: str):
        try:
            client = get_exchange_client(exchange)
            return await client.get_ticker(pair)
        except ExchangeError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def place_order(self, order_data: dict):
        try:
            client = get_exchange_client(order_data["exchange"])
            return await client.place_order(
                pair=order_data["pair"],
                type=order_data["type"],
                side=order_data["side"],
                amount=order_data["amount"],
                price=order_data.get("price")
            )
        except ExchangeError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def cancel_order(self, exchange: str, order_id: str):
        try:
            client = get_exchange_client(exchange)
            return await client.cancel_order(order_id)
        except ExchangeError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def get_balance(self, exchange: str, asset: str):
        try:
            client = get_exchange_client(exchange)
            return await client.get_balance(asset)
        except ExchangeError as e:
            raise HTTPException(status_code=400, detail=str(e))