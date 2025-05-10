import os
import ccxt

class ExchangeClient:
    """Wrapper class for exchange client operations"""
    
    def __init__(self, exchange='kraken', paper_trading=False):
        self.client = get_exchange_client(exchange, paper_trading)
        self.paper_trading = paper_trading
    
    def get_ohlcv(self, symbol, timeframe, limit=100):
        """Get OHLCV data from exchange"""
        return self.client.fetch_ohlcv(symbol, timeframe, limit=limit)
    
    def create_order(self, symbol, type, side, amount, price=None):
        """Create an order on the exchange"""
        if self.paper_trading:
            print(f"[PAPER TRADING] Would create {type} order: {side} {amount} {symbol} @ {price}")
            return {
                'id': 'PAPER-' + str(hash(str((symbol, type, side, amount, price)))),
                'status': 'open',
                'symbol': symbol,
                'type': type,
                'side': side,
                'amount': amount,
                'price': price
            }
        return self.client.create_order(symbol, type, side, amount, price)

    def cancel_order(self, order_id):
        """Cancel an order on the exchange"""
        if self.paper_trading:
            print(f"[PAPER TRADING] Would cancel order {order_id}")
            return True
        return self.client.cancel_order(order_id)

    def get_balances(self):
        """Get account balances"""
        if self.paper_trading:
            print("[PAPER TRADING] Returning mock balances")
            return {
                'USD': 10000.00,
                'BTC': 0.5
            }
        return self.client.fetch_balance()

def get_exchange_client(exchange='kraken', paper_trading=False):
    """
    Initialize and return a ccxt client for the specified exchange.
    Supported exchanges: 'kraken', 'binance'
    """
    exchange = exchange.lower()
    
    if exchange == 'kraken':
        if paper_trading:
            api_key = os.getenv("KRAKEN_PAPER_API_KEY")
            api_secret = os.getenv("KRAKEN_PAPER_API_SECRET")
            if not api_key or not api_secret:
                raise ValueError("KRAKEN_PAPER_API_KEY and/or KRAKEN_PAPER_API_SECRET not set in environment variables.")
        else:
            api_key = os.getenv("KRAKEN_API_KEY")
            api_secret = os.getenv("KRAKEN_API_SECRET")
            if not api_key or not api_secret:
                raise ValueError("KRAKEN_API_KEY and/or KRAKEN_API_SECRET not set in environment variables.")
        
        return ccxt.kraken({
            'apiKey': api_key,
            'secret': api_secret
        })
    elif exchange == 'binance':
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        if not api_key or not api_secret:
            raise ValueError("BINANCE_API_KEY and/or BINANCE_API_SECRET not set in environment variables.")
        return ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'options': {
                'adjustForTimeDifference': True
            }
        })
    else:
        raise ValueError(f"Unsupported exchange: {exchange}")