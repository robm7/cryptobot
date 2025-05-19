import asyncio
import websockets
import json
import logging
from flask_socketio import SocketIO
from .logging_utils import safe_log_info, safe_log_warning, safe_log_error, safe_log_debug # Updated import

logger = logging.getLogger(__name__) # Standard logger instance

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
        uri = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_1m" # Example for Binance 1m klines
        safe_log_info(logger, f"Attempting to connect to WebSocket for {exchange} - {symbol} at {uri}")

        while self.running:
            try:
                async with websockets.connect(uri) as websocket:
                    safe_log_info(logger, f"Connected to {exchange} WebSocket for {symbol}")
                    # Send subscription message if required by the exchange
                    # subscribe_msg = json.dumps({"method": "SUBSCRIBE", "params": [f"{symbol.lower()}@kline_1m"], "id": 1})
                    # await websocket.send(subscribe_msg)
                    # safe_log_debug(logger, f"Sent subscription message for {symbol}")

                    while self.running: # Inner loop for receiving messages
                        try:
                            message = await websocket.recv()
                            safe_log_debug(logger, f"Received raw message for {symbol}: {message[:100]}...")
                            data = json.loads(message)
                            if 'k' in data:
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
                                safe_log_debug(logger, f"Processed kline data for {symbol}: Close={processed_data['close']}, Time={processed_data['timestamp']}")
                                self.socketio.emit(f'realtime_data_{symbol}', processed_data)
                                if symbol in self.active_strategies:
                                    for strategy in self.active_strategies[symbol]:
                                        try:
                                            await strategy.process_realtime_data(processed_data)
                                            safe_log_debug(logger, f"Passed data to strategy {strategy.__class__.__name__} for {symbol}")
                                        except Exception as strat_e:
                                            safe_log_error(logger, f"Error processing data in strategy {strategy.__class__.__name__} for {symbol}: {strat_e}", exc_info=True)
                            else:
                                safe_log_debug(logger, f"Received non-kline message for {symbol}: {data}")
                        except websockets.exceptions.ConnectionClosed: # More specific for recv errors
                            safe_log_warning(logger, f"WebSocket connection closed while receiving for {symbol}. Attempting to reconnect outer loop.")
                            break # Break inner loop to trigger outer loop's reconnect logic
                        except json.JSONDecodeError as e_json:
                            safe_log_error(logger, f"Failed to decode JSON message for {symbol}: {e_json}. Message: {message[:200]}...", exc_info=True)
                            # Continue receiving other messages
                        except Exception as e_recv: # Catch other errors during message handling
                            safe_log_error(logger, f"Error during WebSocket message handling for {symbol}: {e_recv}", exc_info=True)
                            # Depending on severity, might break or continue

            except websockets.exceptions.InvalidStatus as e_status:
                status_code_val = None
                try:
                    # The status_code is on the response attribute of InvalidStatus
                    if hasattr(e_status, 'response') and e_status.response is not None and hasattr(e_status.response, 'status_code'):
                        status_code_val = e_status.response.status_code
                except AttributeError: # Should not happen if attributes exist, but as a safeguard
                    pass

                if status_code_val == 451:
                    safe_log_warning(logger, f"WebSocket connection for {symbol} rejected with status 451 (Unavailable For Legal Reasons). Will not attempt to reconnect this symbol.")
                    break # Exit the 'while self.running' loop for this specific symbol
                else:
                    safe_log_error(logger, f"WebSocket connection for {symbol} failed with InvalidStatus (code: {status_code_val if status_code_val else 'unknown'}): {e_status}. Reconnecting in 10s...", exc_info=True)
                    await asyncio.sleep(10)
            except websockets.exceptions.ConnectionClosedOK: # Should ideally be caught by inner loop's ConnectionClosed
                safe_log_info(logger, f"WebSocket connection closed normally for {symbol}.")
                break # Exit 'while self.running' loop
            except websockets.exceptions.ConnectionClosedError as e_closed_err:
                safe_log_warning(logger, f"WebSocket connection closed unexpectedly for {symbol}: {e_closed_err}. Reconnecting in 5s...")
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                safe_log_info(logger, f"WebSocket task for {symbol} was cancelled.")
                break # Exit main loop on cancellation
            except Exception as e_conn: # Catch other connection errors (e.g., ConnectionRefusedError)
                safe_log_error(logger, f"Unexpected error establishing WebSocket connection for {symbol}: {type(e_conn).__name__} - {e_conn}", exc_info=True)
                safe_log_info(logger, "Waiting 10s before attempting to reconnect...")
                await asyncio.sleep(10)

            if not self.running: # Check after potential sleep/reconnect attempts
                safe_log_info(logger, f"Handler stopped by flag, exiting connection loop for {symbol}.")
                break

        safe_log_info(logger, f"WebSocket connection handler for {symbol} finished.")

    def register_strategy(self, strategy: BaseStrategy, symbol: str):
        """Registers a strategy instance to receive data for a specific symbol."""
        if symbol not in self.active_strategies:
            self.active_strategies[symbol] = []
        if strategy not in self.active_strategies[symbol]:
            self.active_strategies[symbol].append(strategy)
            safe_log_info(logger, f"Registered strategy {strategy.__class__.__name__} for symbol {symbol}")

    def unregister_strategy(self, strategy: BaseStrategy, symbol: str):
        """Unregisters a strategy instance."""
        if symbol in self.active_strategies and strategy in self.active_strategies[symbol]:
            self.active_strategies[symbol].remove(strategy)
            safe_log_info(logger, f"Unregistered strategy {strategy.__class__.__name__} for symbol {symbol}")
            if not self.active_strategies[symbol]:
                del self.active_strategies[symbol]

    async def start(self, subscriptions):
        """Starts the WebSocket connections for the given subscriptions."""
        if self.running:
            safe_log_warning(logger, "RealtimeDataHandler is already running.")
            return

        self.running = True
        tasks = []
        safe_log_info(logger, f"Starting RealtimeDataHandler with {len(subscriptions)} subscriptions.")
        for sub in subscriptions:
            exchange = sub.get('exchange', 'binance')
            symbol = sub.get('symbol')
            if symbol:
                safe_log_info(logger, f"Starting WebSocket connection for {exchange} - {symbol}")
                task = asyncio.create_task(self._handle_connection(exchange, symbol))
                self.connections[symbol] = task
                tasks.append(task)
            else:
                safe_log_warning(logger, f"Subscription missing symbol: {sub}")
        
        if tasks:
            try:
                await asyncio.gather(*tasks)
            except Exception as e:
                safe_log_error(logger, f"Error during asyncio.gather in start: {e}", exc_info=True)
        safe_log_info(logger, "RealtimeDataHandler start method concluded (all tasks gathered or error occurred).")

    async def stop(self):
        """Stops all active WebSocket connections gracefully."""
        safe_log_info(logger, "Stopping RealtimeDataHandler...")
        self.running = False # Signal all loops to stop

        tasks_to_await = []
        for symbol, task in list(self.connections.items()):
            if task and not task.done():
                safe_log_info(logger, f"Requesting cancellation for WebSocket task for {symbol}...")
                task.cancel()
                tasks_to_await.append(task)
            elif task and task.done():
                safe_log_info(logger, f"WebSocket task for {symbol} was already done.")
        
        if tasks_to_await:
            safe_log_info(logger, f"Waiting for {len(tasks_to_await)} WebSocket tasks to complete cancellation...")
            for task in tasks_to_await:
                try:
                    await task
                except asyncio.CancelledError:
                    safe_log_info(logger, f"A WebSocket task was confirmed cancelled for {task.get_name() if hasattr(task, 'get_name') else 'unknown task'}.")
                except Exception as e:
                    safe_log_error(logger, f"A WebSocket task raised an unexpected error during its shutdown: {type(e).__name__} - {e}", exc_info=True)
        else:
            safe_log_info(logger, "No active WebSocket tasks needed to be cancelled.")

        self.connections.clear()
        self.active_strategies.clear()
        safe_log_info(logger, "RealtimeDataHandler stopped successfully.")

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