"""
Advanced order types implementation for cryptocurrency exchanges.
This module provides support for complex order types like OCO (One-Cancels-Other),
trailing stops, and other advanced order types that may not be directly supported
by all exchanges.
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)

class AdvancedOrderManager:
    """
    Manages advanced order types by coordinating multiple simple orders
    when necessary. Provides a unified interface for advanced order types
    across different exchanges.
    """
    
    def __init__(self, exchange_client):
        """
        Initialize the advanced order manager.
        
        Args:
            exchange_client: The exchange client to use for order execution
        """
        self.exchange_client = exchange_client
        self.managed_orders = {}  # Track orders being managed
        self.running_tasks = {}   # Track background tasks
        
    async def create_oco_order(self, symbol: str, side: str, amount: float, 
                             price: float, stop_price: float, 
                             stop_limit_price: Optional[float] = None,
                             params: Optional[Dict] = None) -> Dict:
        """
        Create a One-Cancels-Other (OCO) order.
        
        An OCO order is a pair of orders: a limit order and a stop order.
        When one order executes, the other is automatically canceled.
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order quantity
            price: Limit order price
            stop_price: Stop trigger price
            stop_limit_price: Optional price for stop-limit (defaults to stop_price)
            params: Additional exchange-specific parameters
            
        Returns:
            dict: Order information
        """
        # Delegate to exchange client's implementation if it has native support
        if hasattr(self.exchange_client, 'create_oco_order'):
            return await self.exchange_client.create_oco_order(
                symbol, side, amount, price, stop_price, stop_limit_price, params
            )
            
        # Otherwise implement OCO using two separate orders and monitoring
        logger.info(f"Creating managed OCO order for {symbol}: {side} {amount} @ {price}/{stop_price}")
        
        # Create the limit order
        limit_order = await self.exchange_client.create_order(
            symbol=symbol,
            type='limit',
            side=side,
            amount=amount,
            price=price,
            params=params
        )
        
        # Create the stop order
        stop_params = params.copy() if params else {}
        if stop_limit_price:
            stop_type = 'stop_limit'
            stop_params['stopPrice'] = stop_price
            stop_order = await self.exchange_client.create_order(
                symbol=symbol,
                type=stop_type,
                side=side,
                amount=amount,
                price=stop_limit_price,
                params=stop_params
            )
        else:
            stop_type = 'stop_market'
            stop_params['stopPrice'] = stop_price
            stop_order = await self.exchange_client.create_order(
                symbol=symbol,
                type=stop_type,
                side=side,
                amount=amount,
                params=stop_params
            )
        
        # Create a unique ID for this OCO order
        oco_id = f"OCO-{limit_order['id']}-{stop_order['id']}"
        
        # Store the order details
        self.managed_orders[oco_id] = {
            'type': 'oco',
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price,
            'stop_price': stop_price,
            'limit_order_id': limit_order['id'],
            'stop_order_id': stop_order['id'],
            'status': 'open',
            'created_at': datetime.now().timestamp()
        }
        
        # Start a background task to monitor these orders
        self.running_tasks[oco_id] = asyncio.create_task(
            self._monitor_oco_order(oco_id, symbol, limit_order['id'], stop_order['id'])
        )
        
        # Return combined order info
        return {
            'id': oco_id,
            'status': 'open',
            'symbol': symbol,
            'type': 'oco',
            'side': side,
            'amount': amount,
            'price': price,
            'stop_price': stop_price,
            'limit_order_id': limit_order['id'],
            'stop_order_id': stop_order['id'],
            'timestamp': datetime.now().timestamp() * 1000,
            'datetime': datetime.now().isoformat()
        }
    
    async def create_trailing_stop_order(self, symbol: str, side: str, amount: float,
                                       activation_price: Optional[float] = None,
                                       callback_rate: Optional[float] = None,
                                       params: Optional[Dict] = None) -> Dict:
        """
        Create a trailing stop order.
        
        A trailing stop order adjusts the stop price as the market price changes,
        maintaining a specified distance (the callback rate).
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order quantity
            activation_price: Price at which trailing stop becomes active
            callback_rate: Callback rate in percentage (e.g., 1.0 for 1%)
            params: Additional exchange-specific parameters
            
        Returns:
            dict: Order information
        """
        # Delegate to exchange client's implementation if it has native support
        if hasattr(self.exchange_client, 'create_trailing_stop_order'):
            return await self.exchange_client.create_trailing_stop_order(
                symbol, side, amount, activation_price, callback_rate, params
            )
            
        # Otherwise implement trailing stop using monitoring and order updates
        logger.info(f"Creating managed trailing stop for {symbol}: {side} {amount} with {callback_rate}% callback")
        
        # Get current market price if activation price not specified
        if not activation_price:
            ticker = await self.exchange_client.get_ticker(symbol)
            activation_price = ticker['last']
        
        # Calculate initial stop price based on side and callback rate
        if side.lower() == 'sell':
            # For sell orders, stop price is below market price
            stop_price = activation_price * (1 - callback_rate / 100)
        else:
            # For buy orders, stop price is above market price
            stop_price = activation_price * (1 + callback_rate / 100)
        
        # Create a unique ID for this trailing stop
        trailing_id = f"TRAILING-{symbol}-{int(time.time() * 1000)}"
        
        # Store the order details without creating an actual order yet
        self.managed_orders[trailing_id] = {
            'type': 'trailing_stop',
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'activation_price': activation_price,
            'callback_rate': callback_rate,
            'current_stop_price': stop_price,
            'highest_price': activation_price if side.lower() == 'sell' else 0,
            'lowest_price': activation_price if side.lower() == 'buy' else float('inf'),
            'order_id': None,  # No order created yet
            'status': 'pending',  # Waiting for activation
            'created_at': datetime.now().timestamp()
        }
        
        # Start a background task to monitor market and manage the trailing stop
        self.running_tasks[trailing_id] = asyncio.create_task(
            self._monitor_trailing_stop(trailing_id, symbol, side, amount, activation_price, callback_rate)
        )
        
        # Return order info
        return {
            'id': trailing_id,
            'status': 'pending',
            'symbol': symbol,
            'type': 'trailing_stop',
            'side': side,
            'amount': amount,
            'activation_price': activation_price,
            'callback_rate': callback_rate,
            'current_stop_price': stop_price,
            'timestamp': datetime.now().timestamp() * 1000,
            'datetime': datetime.now().isoformat()
        }
    
    async def cancel_advanced_order(self, order_id: str) -> Dict:
        """
        Cancel an advanced order.
        
        Args:
            order_id: The ID of the advanced order to cancel
            
        Returns:
            dict: Cancellation result
        """
        if order_id not in self.managed_orders:
            return {'success': False, 'error': 'Order not found'}
        
        order = self.managed_orders[order_id]
        
        # Cancel any running monitoring task
        if order_id in self.running_tasks:
            self.running_tasks[order_id].cancel()
            del self.running_tasks[order_id]
        
        # Cancel actual exchange orders based on order type
        if order['type'] == 'oco':
            # Cancel both limit and stop orders
            limit_cancelled = await self.exchange_client.cancel_order(
                order['limit_order_id'], order['symbol']
            )
            stop_cancelled = await self.exchange_client.cancel_order(
                order['stop_order_id'], order['symbol']
            )
            success = limit_cancelled or stop_cancelled
            
        elif order['type'] == 'trailing_stop':
            # If an actual stop order was placed, cancel it
            if order['order_id']:
                success = await self.exchange_client.cancel_order(
                    order['order_id'], order['symbol']
                )
            else:
                # No actual order was placed yet
                success = True
        
        # Update order status
        if success:
            order['status'] = 'canceled'
            
        return {
            'success': success,
            'order_id': order_id,
            'status': order['status']
        }
    
    async def get_advanced_order_status(self, order_id: str) -> Dict:
        """
        Get the status of an advanced order.
        
        Args:
            order_id: The ID of the advanced order
            
        Returns:
            dict: Order status information
        """
        if order_id not in self.managed_orders:
            return {'status': 'error', 'message': 'Order not found'}
        
        order = self.managed_orders[order_id]
        
        # For OCO orders, check both component orders
        if order['type'] == 'oco':
            try:
                limit_status = await self.exchange_client.get_order_status(
                    order['limit_order_id'], order['symbol']
                )
                stop_status = await self.exchange_client.get_order_status(
                    order['stop_order_id'], order['symbol']
                )
                
                # Determine overall status
                if limit_status['status'] == 'filled':
                    order['status'] = 'filled'
                    order['filled_by'] = 'limit'
                elif stop_status['status'] == 'filled':
                    order['status'] = 'filled'
                    order['filled_by'] = 'stop'
                elif limit_status['status'] == 'canceled' and stop_status['status'] == 'canceled':
                    order['status'] = 'canceled'
                else:
                    order['status'] = 'open'
                    
                return {
                    'id': order_id,
                    'status': order['status'],
                    'symbol': order['symbol'],
                    'type': 'oco',
                    'limit_order': limit_status,
                    'stop_order': stop_status
                }
                
            except Exception as e:
                logger.error(f"Error checking OCO order status: {e}")
                return {
                    'id': order_id,
                    'status': order['status'],
                    'error': str(e)
                }
                
        # For trailing stop orders
        elif order['type'] == 'trailing_stop':
            # If an actual order was placed, check its status
            if order['order_id']:
                try:
                    stop_status = await self.exchange_client.get_order_status(
                        order['order_id'], order['symbol']
                    )
                    
                    if stop_status['status'] == 'filled':
                        order['status'] = 'filled'
                    elif stop_status['status'] == 'canceled':
                        order['status'] = 'canceled'
                        
                    return {
                        'id': order_id,
                        'status': order['status'],
                        'symbol': order['symbol'],
                        'type': 'trailing_stop',
                        'activation_price': order['activation_price'],
                        'callback_rate': order['callback_rate'],
                        'current_stop_price': order['current_stop_price'],
                        'order_details': stop_status
                    }
                    
                except Exception as e:
                    logger.error(f"Error checking trailing stop order status: {e}")
                    return {
                        'id': order_id,
                        'status': order['status'],
                        'error': str(e)
                    }
            else:
                # No actual order placed yet
                return {
                    'id': order_id,
                    'status': order['status'],
                    'symbol': order['symbol'],
                    'type': 'trailing_stop',
                    'activation_price': order['activation_price'],
                    'callback_rate': order['callback_rate'],
                    'current_stop_price': order['current_stop_price']
                }
        
        # Fallback for unknown order types
        return {
            'id': order_id,
            'status': order['status'],
            'type': order['type']
        }
    
    async def _monitor_oco_order(self, oco_id: str, symbol: str, 
                               limit_order_id: str, stop_order_id: str):
        """
        Monitor an OCO order and ensure that when one order fills,
        the other is canceled.
        
        Args:
            oco_id: The OCO order ID
            symbol: Trading pair symbol
            limit_order_id: The limit order ID
            stop_order_id: The stop order ID
        """
        try:
            while oco_id in self.managed_orders:
                # Check status of both orders
                limit_status = await self.exchange_client.get_order_status(limit_order_id, symbol)
                stop_status = await self.exchange_client.get_order_status(stop_order_id, symbol)
                
                # If either order filled, cancel the other
                if limit_status['status'] == 'filled':
                    logger.info(f"OCO limit order filled: {limit_order_id}, canceling stop order: {stop_order_id}")
                    await self.exchange_client.cancel_order(stop_order_id, symbol)
                    self.managed_orders[oco_id]['status'] = 'filled'
                    self.managed_orders[oco_id]['filled_by'] = 'limit'
                    break
                    
                elif stop_status['status'] == 'filled':
                    logger.info(f"OCO stop order filled: {stop_order_id}, canceling limit order: {limit_order_id}")
                    await self.exchange_client.cancel_order(limit_order_id, symbol)
                    self.managed_orders[oco_id]['status'] = 'filled'
                    self.managed_orders[oco_id]['filled_by'] = 'stop'
                    break
                    
                # If both orders are canceled, the OCO is canceled
                elif limit_status['status'] == 'canceled' and stop_status['status'] == 'canceled':
                    logger.info(f"Both OCO orders canceled: {oco_id}")
                    self.managed_orders[oco_id]['status'] = 'canceled'
                    break
                
                # Wait before checking again
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            logger.info(f"OCO monitoring canceled for {oco_id}")
            
        except Exception as e:
            logger.error(f"Error monitoring OCO order {oco_id}: {e}")
            
        finally:
            # Clean up
            if oco_id in self.running_tasks:
                del self.running_tasks[oco_id]
    
    async def _monitor_trailing_stop(self, order_id: str, symbol: str, side: str, 
                                   amount: float, activation_price: float, 
                                   callback_rate: float):
        """
        Monitor market price and manage a trailing stop order.
        
        Args:
            order_id: The trailing stop order ID
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order quantity
            activation_price: Price at which trailing stop becomes active
            callback_rate: Callback rate in percentage
        """
        try:
            order = self.managed_orders[order_id]
            is_sell = side.lower() == 'sell'
            
            # Wait for price to reach activation price
            while order['status'] == 'pending':
                ticker = await self.exchange_client.get_ticker(symbol)
                current_price = ticker['last']
                
                # Check if activation price is reached
                if (is_sell and current_price >= activation_price) or \
                   (not is_sell and current_price <= activation_price):
                    logger.info(f"Trailing stop activated for {order_id} at price {current_price}")
                    order['status'] = 'active'
                    
                    # Initialize tracking values
                    if is_sell:
                        order['highest_price'] = current_price
                        order['current_stop_price'] = current_price * (1 - callback_rate / 100)
                    else:
                        order['lowest_price'] = current_price
                        order['current_stop_price'] = current_price * (1 + callback_rate / 100)
                else:
                    await asyncio.sleep(5)
            
            # Once activated, track price movements and adjust stop price
            while order['status'] == 'active':
                ticker = await self.exchange_client.get_ticker(symbol)
                current_price = ticker['last']
                
                if is_sell:
                    # For sell orders, track highest price and adjust stop upward
                    if current_price > order['highest_price']:
                        order['highest_price'] = current_price
                        new_stop_price = current_price * (1 - callback_rate / 100)
                        
                        # Only move stop price upward
                        if new_stop_price > order['current_stop_price']:
                            order['current_stop_price'] = new_stop_price
                            logger.info(f"Trailing stop updated for {order_id}: new stop price {new_stop_price}")
                    
                    # Check if stop is triggered
                    if current_price <= order['current_stop_price']:
                        logger.info(f"Trailing stop triggered for {order_id} at price {current_price}")
                        
                        # Place actual stop market order
                        stop_order = await self.exchange_client.create_order(
                            symbol=symbol,
                            type='market',
                            side=side,
                            amount=amount
                        )
                        
                        order['order_id'] = stop_order['id']
                        order['status'] = 'filled'
                        order['executed_price'] = current_price
                        break
                        
                else:
                    # For buy orders, track lowest price and adjust stop downward
                    if current_price < order['lowest_price']:
                        order['lowest_price'] = current_price
                        new_stop_price = current_price * (1 + callback_rate / 100)
                        
                        # Only move stop price downward
                        if new_stop_price < order['current_stop_price']:
                            order['current_stop_price'] = new_stop_price
                            logger.info(f"Trailing stop updated for {order_id}: new stop price {new_stop_price}")
                    
                    # Check if stop is triggered
                    if current_price >= order['current_stop_price']:
                        logger.info(f"Trailing stop triggered for {order_id} at price {current_price}")
                        
                        # Place actual stop market order
                        stop_order = await self.exchange_client.create_order(
                            symbol=symbol,
                            type='market',
                            side=side,
                            amount=amount
                        )
                        
                        order['order_id'] = stop_order['id']
                        order['status'] = 'filled'
                        order['executed_price'] = current_price
                        break
                
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            logger.info(f"Trailing stop monitoring canceled for {order_id}")
            
        except Exception as e:
            logger.error(f"Error monitoring trailing stop order {order_id}: {e}")
            
        finally:
            # Clean up
            if order_id in self.running_tasks:
                del self.running_tasks[order_id]