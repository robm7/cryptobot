import asyncio
import websockets
import json
import logging
from flask_socketio import SocketIO

logger = logging.getLogger(__name__) # Ensure logger is defined at module level

from strategies.base_strategy import BaseStrategy # Assuming a base class
from typing import List, Dict

class RealtimeDataHandler:
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.connections = {} # Stores asyncio tasks for each symbol
        self.running = False
        self.active_strategies: Dict[str, List[BaseStrategy]] = {} # Maps symbol -> list of strategies

    async def _handle_connection(self, exchange, symbol):
        """Handles a single WebSocket connection for a given exchange and symbol."""
        # Replace with actual exchange WebSocket endpoint and subscription message
        # Example using a generic websocket library
        # TODO: Make the URI dynamic based on the 'exchange' parameter
        uri = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_1m" # Example for Binance 1m klines
        logger.info(f"Attempting to connect to WebSocket for {exchange} - {symbol} at {uri}")

        while self.running:
            try:
                async with websockets.connect(uri) as websocket:
                    logger.info(f"Connected to {exchange} WebSocket for {symbol}")
                    # Send subscription message if required by the exchange
                    # subscribe_msg = json.dumps({"method": "SUBSCRIBE", "params": [f"{symbol.lower()}@kline_1m"], "id": 1})
                    # await websocket.send(subscribe_msg)
                    # logger.debug(f"Sent subscription message for {symbol}")

                    while self.running:
                        message = await websocket.recv()
                        logger.debug(f"Received raw message for {symbol}: {message[:100]}...") # Log truncated message
                        data = json.loads(message)
                        # Process the received data (e.g., extract kline info)
                        if 'k' in data: # Example processing for Binance kline stream
                            kline = data['k']
                            processed_data = {
                                'symbol': data['s'],
                                'timestamp': data['E'],
                                'open': kline['o'],
                                'high': kline['h'],
                                'low': kline['l'],
                                'close': kline['c'],
                                'volume': kline['v'],
                                'is_closed': kline['x']
                            }
                            logger.debug(f"Processed kline data for {symbol}: Close={processed_data['close']}, Time={processed_data['timestamp']}")
                            # Emit data to frontend via SocketIO
                            self.socketio.emit(f'realtime_data_{symbol}', processed_data)
                            # Pass data to relevant strategies
                            if symbol in self.active_strategies:
                                for strategy in self.active_strategies[symbol]:
                                    try:
                                        # Assuming strategies have a method to process single data points
                                        await strategy.process_realtime_data(processed_data)
                                        logger.debug(f"Passed data to strategy {strategy.__class__.__name__} for {symbol}")
                                    except Exception as strat_e:
                                        logger.error(f"Error processing data in strategy {strategy.__class__.__name__} for {symbol}: {strat_e}", exc_info=True)
                        else:
                            logger.debug(f"Received non-kline message for {symbol}: {data}")

            except websockets.exceptions.ConnectionClosedOK:
                logger.info(f"WebSocket connection closed normally for {symbol}.")
                break # Exit inner loop if closed normally
            except websockets.exceptions.ConnectionClosedError as e:
                logger.warning(f"WebSocket connection closed unexpectedly for {symbol}: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5) # Wait before reconnecting
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON message for {symbol}: {e}. Message: {message[:200]}...", exc_info=True)
                # Decide whether to continue or break/reconnect
            except Exception as e:
                logger.error(f"Unexpected error in WebSocket handler for {symbol}: {e}", exc_info=True)
                logger.info("Waiting 10s before attempting to reconnect...")
                await asyncio.sleep(10) # Wait longer on general errors

            if not self.running:
                logger.info(f"Handler stopped, exiting connection loop for {symbol}.")
                break # Exit outer loop if handler stopped

        logger.info(f"WebSocket connection handler for {symbol} finished.")

    def register_strategy(self, strategy: BaseStrategy, symbol: str):
        """Registers a strategy instance to receive data for a specific symbol."""
        if symbol not in self.active_strategies:
            self.active_strategies[symbol] = []
        if strategy not in self.active_strategies[symbol]:
            self.active_strategies[symbol].append(strategy)
            logger.info(f"Registered strategy {strategy.__class__.__name__} for symbol {symbol}")

    def unregister_strategy(self, strategy: BaseStrategy, symbol: str):
        """Unregisters a strategy instance."""
        if symbol in self.active_strategies and strategy in self.active_strategies[symbol]:
            self.active_strategies[symbol].remove(strategy)
            logger.info(f"Unregistered strategy {strategy.__class__.__name__} for symbol {symbol}")
            if not self.active_strategies[symbol]: # Remove symbol entry if no strategies left
                del self.active_strategies[symbol]

    async def start(self, subscriptions):
        """Starts the WebSocket connections for the given subscriptions."""
        if self.running:
            logger.warning("RealtimeDataHandler is already running.")
            return

        self.running = True
        tasks = []
        logger.info(f"Starting RealtimeDataHandler with {len(subscriptions)} subscriptions.")
        for sub in subscriptions:
            exchange = sub.get('exchange', 'binance') # Default to binance or get from sub
            symbol = sub.get('symbol')
            if symbol:
                logger.info(f"Starting WebSocket connection for {exchange} - {symbol}")
                task = asyncio.create_task(self._handle_connection(exchange, symbol))
                self.connections[symbol] = task
                tasks.append(task)
            else:
                logger.warning(f"Subscription missing symbol: {sub}")
        
        if tasks:
            await asyncio.gather(*tasks)
        logger.info("RealtimeDataHandler stopped.")

    async def stop(self):
        """Stops all active WebSocket connections."""
        logger.info("Stopping RealtimeDataHandler...")
        self.running = False
        cancelled_tasks = []
        for symbol, task in self.connections.items():
            if task and not task.done():
                task.cancel()
                logger.info(f"Cancelled WebSocket task for {symbol}")
        self.connections = {}
        self.active_strategies = {} # Clear strategies on stop
        logger.info("RealtimeDataHandler stopped successfully.")

# Example usage (typically integrated into the Flask app)
# async def main():
#     # Dummy SocketIO for standalone testing
#     class DummySocketIO:
#         def emit(self, event, data):
#             print(f"Emitting {event}: {data}")
    
#     handler = RealtimeDataHandler(DummySocketIO())
#     subscriptions = [
#         {'exchange': 'binance', 'symbol': 'BTCUSDT'},
#         {'exchange': 'binance', 'symbol': 'ETHUSDT'}
#     ]
#     try:
#         await handler.start(subscriptions)
#     except KeyboardInterrupt:
#         await handler.stop()

# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     asyncio.run(main())