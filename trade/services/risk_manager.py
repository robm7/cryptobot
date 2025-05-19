"""
Risk Manager Service

This module provides a comprehensive risk management system that integrates
with the trading engine to enforce risk limits and provide risk-based position sizing.
"""
from typing import Dict, List, Tuple, Optional, Any, Union
from decimal import Decimal
import logging
import time
from datetime import datetime, timedelta
import asyncio
import numpy as np

from ..config.risk_config import risk_config
from ..schemas.trade import MarketOrder, LimitOrder, RiskParameters
from ..services.portfolio import PortfolioService
from ..utils.circuit_breaker import CircuitBreaker
from ..utils.alerting import AlertManager
from ..utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Comprehensive risk management service that integrates with the trading engine.
    
    This service:
    - Validates trades against risk parameters before execution
    - Monitors ongoing risk exposure
    - Can halt trading when risk thresholds are exceeded
    - Provides risk metrics and reporting
    - Implements risk-based position sizing
    """
    
    def __init__(self, portfolio_service: PortfolioService, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize the risk manager.
        
        Args:
            portfolio_service: Portfolio service for tracking positions and exposure
            metrics_collector: Optional metrics collector for recording risk metrics
        """
        self.portfolio_service = portfolio_service
        self.metrics_collector = metrics_collector
        self.alert_manager = AlertManager()
        
        # Initialize circuit breakers for each symbol
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Track daily and weekly metrics
        self.daily_trades_count: Dict[str, int] = {}  # symbol -> count
        self.daily_pnl: Dict[str, Decimal] = {}  # symbol -> pnl
        self.weekly_pnl: Dict[str, Decimal] = {}  # symbol -> pnl
        
        # Track last reset time for daily/weekly counters
        self.last_daily_reset = datetime.now()
        self.last_weekly_reset = datetime.now()
        
        # Risk monitoring task
        self.monitoring_task = None
        self.monitoring_active = False
        
        # Trading halt flags
        self.trading_halted = False
        self.trading_halt_reason = ""
        
        # Initialize risk limits
        self.risk_limits = risk_config.get_risk_limits()
        
        logger.info("Risk Manager initialized with limits: %s", self.risk_limits)
    
    async def start_monitoring(self):
        """Start the risk monitoring background task"""
        if self.monitoring_task is None:
            self.monitoring_active = True
            self.monitoring_task = asyncio.create_task(self._risk_monitoring_loop())
            logger.info("Risk monitoring started")
    
    async def stop_monitoring(self):
        """Stop the risk monitoring background task"""
        if self.monitoring_task is not None:
            self.monitoring_active = False
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
            logger.info("Risk monitoring stopped")
    
    async def _risk_monitoring_loop(self):
        """Background task that periodically checks risk metrics"""
        while self.monitoring_active:
            try:
                await self._check_risk_metrics()
                await self._reset_time_based_counters()
                
                # Record metrics if collector is available
                if self.metrics_collector:
                    portfolio_risk = await self.portfolio_service.calculate_portfolio_risk()
                    self.metrics_collector.record_gauge("risk.portfolio.exposure", float(portfolio_risk["total_exposure"]))
                    self.metrics_collector.record_gauge("risk.portfolio.drawdown", float(portfolio_risk["current_drawdown"]))
                
                # Sleep until next check
                await asyncio.sleep(risk_config.RISK_MONITORING_INTERVAL_SECONDS)
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Sleep on error to avoid tight loop
    
    async def _check_risk_metrics(self):
        """Check risk metrics and take action if thresholds are exceeded"""
        # Get current portfolio risk
        portfolio_risk = await self.portfolio_service.calculate_portfolio_risk()
        
        # Check for critical drawdown
        if portfolio_risk["current_drawdown"] >= risk_config.CRITICAL_DRAWDOWN_THRESHOLD:
            await self._halt_trading(f"Critical drawdown threshold exceeded: {float(portfolio_risk['current_drawdown']):.2%}")
            return
        
        # Check for excessive exposure
        if portfolio_risk["total_exposure"] > self.risk_limits["max_portfolio_exposure"]:
            # Alert but don't halt trading
            self.alert_manager.send_alert(
                "Portfolio exposure exceeds limit",
                f"Current exposure: {float(portfolio_risk['total_exposure'])}, Limit: {float(self.risk_limits['max_portfolio_exposure'])}"
            )
        
        # Check daily drawdown
        daily_pnl_sum = sum(self.daily_pnl.values())
        account_equity = await self.portfolio_service.get_account_equity()
        daily_drawdown = abs(daily_pnl_sum) / account_equity if daily_pnl_sum < 0 else Decimal(0)
        
        if daily_drawdown > self.risk_limits["max_daily_drawdown"]:
            await self._halt_trading(f"Daily drawdown limit exceeded: {float(daily_drawdown):.2%}")
            return
        
        # Check weekly drawdown
        weekly_pnl_sum = sum(self.weekly_pnl.values())
        weekly_drawdown = abs(weekly_pnl_sum) / account_equity if weekly_pnl_sum < 0 else Decimal(0)
        
        if weekly_drawdown > self.risk_limits["max_weekly_drawdown"]:
            await self._halt_trading(f"Weekly drawdown limit exceeded: {float(weekly_drawdown):.2%}")
            return
        
        # If we were halted but conditions are now acceptable, resume trading
        if self.trading_halted:
            # Only resume if drawdown has improved significantly
            if portfolio_risk["current_drawdown"] < risk_config.CRITICAL_DRAWDOWN_THRESHOLD * Decimal("0.8"):
                self._resume_trading("Risk conditions have improved")
    
    async def _reset_time_based_counters(self):
        """Reset daily and weekly counters when appropriate"""
        now = datetime.now()
        
        # Reset daily counters if it's a new day
        if now.date() > self.last_daily_reset.date():
            self.daily_trades_count = {}
            self.daily_pnl = {}
            self.last_daily_reset = now
            logger.info("Daily risk counters reset")
        
        # Reset weekly counters if it's a new week
        if now.date() - self.last_weekly_reset.date() >= timedelta(days=7):
            self.weekly_pnl = {}
            self.last_weekly_reset = now
            logger.info("Weekly risk counters reset")
    
    async def _halt_trading(self, reason: str):
        """Halt all trading due to risk limit violation"""
        if not self.trading_halted:
            self.trading_halted = True
            self.trading_halt_reason = reason
            logger.critical(f"TRADING HALTED: {reason}")
            
            # Send alert
            self.alert_manager.send_alert(
                "TRADING HALTED",
                f"Reason: {reason}",
                level="critical"
            )
    
    def _resume_trading(self, reason: str):
        """Resume trading after a halt"""
        if self.trading_halted:
            self.trading_halted = False
            self.trading_halt_reason = ""
            logger.info(f"Trading resumed: {reason}")
            
            # Send alert
            self.alert_manager.send_alert(
                "Trading resumed",
                f"Reason: {reason}",
                level="info"
            )
    
    async def validate_order(self, order: Union[MarketOrder, LimitOrder], 
                           account_equity: Optional[Decimal] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate an order against all risk parameters.
        
        Args:
            order: The order to validate
            account_equity: Current account equity (optional)
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        # Check if trading is halted
        if self.trading_halted:
            return False, f"Trading is currently halted: {self.trading_halt_reason}"
        
        # Check circuit breaker
        if order.symbol in self.circuit_breakers and self.circuit_breakers[order.symbol].is_triggered():
            return False, f"Circuit breaker triggered for {order.symbol}"
        
        try:
            # Get account equity if not provided
            if account_equity is None:
                account_equity = await self.portfolio_service.get_account_equity()
            
            # Get current drawdown
            drawdown_metrics = self.portfolio_service.get_drawdown_metrics()
            current_drawdown = drawdown_metrics["current_drawdown"]
            
            # Check per-trade risk limits
            
            # 1. Check max order size
            order_value = self._calculate_order_value(order)
            if order_value > self.risk_limits["max_order_size"]:
                return False, f"Order size ({float(order_value)}) exceeds maximum allowed ({float(self.risk_limits['max_order_size'])})"
            
            # 2. Check risk per trade
            risk_amount = self._calculate_order_risk(order, account_equity)
            max_risk_amount = account_equity * self.risk_limits["risk_per_trade"]
            if risk_amount > max_risk_amount:
                return False, f"Order risk ({float(risk_amount)}) exceeds maximum allowed ({float(max_risk_amount)})"
            
            # Check per-symbol risk limits
            
            # 3. Check symbol exposure
            current_exposure = await self.portfolio_service.get_symbol_exposure(order.symbol)
            new_exposure = current_exposure + order_value if order.side == "buy" else current_exposure
            if new_exposure > self.risk_limits["max_symbol_exposure"]:
                return False, f"Symbol exposure ({float(new_exposure)}) would exceed maximum allowed ({float(self.risk_limits['max_symbol_exposure'])})"
            
            # 4. Check symbol concentration
            portfolio_value = await self.portfolio_service.get_portfolio_value()
            new_concentration = new_exposure / portfolio_value if portfolio_value > 0 else Decimal(0)
            if new_concentration > self.risk_limits["max_symbol_concentration"]:
                return False, f"Symbol concentration ({float(new_concentration):.2%}) would exceed maximum allowed ({float(self.risk_limits['max_symbol_concentration']):.2%})"
            
            # Check portfolio-level risk limits
            
            # 5. Check portfolio exposure
            total_exposure = await self.portfolio_service.get_total_exposure()
            new_total_exposure = total_exposure + order_value if order.side == "buy" else total_exposure
            if new_total_exposure > self.risk_limits["max_portfolio_exposure"]:
                return False, f"Portfolio exposure ({float(new_total_exposure)}) would exceed maximum allowed ({float(self.risk_limits['max_portfolio_exposure'])})"
            
            # 6. Check leverage
            new_leverage = new_total_exposure / account_equity if account_equity > 0 else Decimal(0)
            if new_leverage > self.risk_limits["max_leverage"]:
                return False, f"Leverage ({float(new_leverage):.2f}x) would exceed maximum allowed ({float(self.risk_limits['max_leverage'])}x)"
            
            # 7. Check correlation risk
            position_risk = await self.portfolio_service.get_position_risk(order.symbol, order_value)
            if position_risk["correlation_risk"] > self.risk_limits["max_correlation"]:
                return False, f"Correlation risk ({float(position_risk['correlation_risk']):.2f}) exceeds maximum allowed ({float(self.risk_limits['max_correlation'])})"
            
            # Check time-based risk limits
            
            # 8. Check daily trade count
            daily_count = self.daily_trades_count.get(order.symbol, 0)
            if daily_count >= self.risk_limits["max_trades_per_day"]:
                return False, f"Daily trade count ({daily_count}) for {order.symbol} would exceed maximum allowed ({self.risk_limits['max_trades_per_day']})"
            
            # 9. Check drawdown limits
            if current_drawdown > risk_config.CRITICAL_DRAWDOWN_THRESHOLD:
                return False, f"Trading halted - drawdown ({float(current_drawdown):.2%}) exceeds critical threshold ({float(risk_config.CRITICAL_DRAWDOWN_THRESHOLD):.2%})"
            
            # All checks passed
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating order: {e}", exc_info=True)
            return False, f"Error validating order: {str(e)}"
    
    async def calculate_position_size(self, symbol: str, 
                                    account_equity: Decimal,
                                    risk_percentage: Optional[Decimal] = None,
                                    stop_loss_pct: Optional[Decimal] = None,
                                    volatility_factor: bool = True,
                                    current_drawdown: Optional[Decimal] = None) -> Decimal:
        """
        Calculate optimal position size based on risk parameters.
        
        Args:
            symbol: Trading pair symbol
            account_equity: Current account equity
            risk_percentage: Percentage of account to risk (overrides default)
            stop_loss_pct: Stop loss percentage (if applicable)
            volatility_factor: Whether to adjust for volatility
            current_drawdown: Current drawdown as a decimal
            
        Returns:
            Decimal: Calculated position size in quote currency
        """
        # Use custom risk percentage if provided, otherwise use default
        risk_per_trade = risk_percentage if risk_percentage is not None else self.risk_limits["risk_per_trade"]
        
        # Get current drawdown if not provided
        if current_drawdown is None:
            drawdown_metrics = self.portfolio_service.get_drawdown_metrics()
            current_drawdown = drawdown_metrics["current_drawdown"]
        
        # Base position size calculation
        base_size = account_equity * risk_per_trade
        
        # Adjust for stop loss if provided
        if stop_loss_pct and stop_loss_pct > Decimal("0"):
            base_size = base_size / stop_loss_pct
        
        # Apply volatility scaling if enabled
        if volatility_factor and risk_config.VOLATILITY_SCALING_ENABLED:
            # Get volatility metrics
            position_risk = await self.portfolio_service.get_position_risk(symbol, base_size)
            volatility = Decimal(str(position_risk["volatility"]))
            
            # Calculate volatility adjustment factor
            if volatility > risk_config.VOLATILITY_BASELINE:
                # Calculate how much volatility exceeds baseline (as a ratio)
                excess_volatility_ratio = (volatility / risk_config.VOLATILITY_BASELINE) - Decimal("1.0")
                
                # Apply non-linear scaling (square root) to avoid too drastic reductions
                adjustment_factor = Decimal("1.0") - (risk_config.VOLATILITY_MAX_ADJUSTMENT *
                                                  (Decimal(str(np.sqrt(float(excess_volatility_ratio)))))
                                                 )
                
                # Ensure adjustment doesn't go below minimum threshold (25% of original size)
                adjustment_factor = max(adjustment_factor, Decimal("0.25"))
                
                # Apply adjustment
                base_size = base_size * adjustment_factor
                logger.info(f"Volatility adjustment for {symbol}: {float(adjustment_factor):.2f}x (vol: {float(volatility):.2f})")
        
        # Apply drawdown controls if enabled
        if risk_config.DRAWDOWN_CONTROL_ENABLED and current_drawdown > Decimal("0"):
            # Apply progressive scaling based on drawdown severity
            if current_drawdown < risk_config.MAX_DRAWDOWN_THRESHOLD:
                # Scale down linearly between 5% and MAX_DRAWDOWN_THRESHOLD
                if current_drawdown > Decimal("0.05"):
                    # Calculate how far between 5% and threshold (0.0 to 1.0)
                    severity = (current_drawdown - Decimal("0.05")) / (risk_config.MAX_DRAWDOWN_THRESHOLD - Decimal("0.05"))
                    # Apply scaling factor (more aggressive with higher DRAWDOWN_SCALING_FACTOR)
                    reduction_factor = Decimal("1.0") - (severity * Decimal("0.5") * risk_config.DRAWDOWN_SCALING_FACTOR)
                    base_size = base_size * reduction_factor
                    logger.info(f"Drawdown control: {float(current_drawdown):.2%} drawdown, reducing position to {float(reduction_factor):.2%} of normal size")
            elif current_drawdown < risk_config.CRITICAL_DRAWDOWN_THRESHOLD:
                # Severe drawdown - more aggressive reduction (25% of normal size)
                base_size = base_size * Decimal("0.25")
                logger.warning(f"Severe drawdown detected: {float(current_drawdown):.2%}, reducing position to 25% of normal size")
            else:
                # Critical drawdown - minimal position size (10% of normal)
                base_size = base_size * Decimal("0.1")
                logger.critical(f"Critical drawdown detected: {float(current_drawdown):.2%}, reducing position to 10% of normal size")
        
        # Apply correlation adjustment
        position_risk = await self.portfolio_service.get_position_risk(symbol, base_size)
        if position_risk["correlation_risk"] > Decimal("0.5"):
            # Reduce position size based on correlation
            correlation_factor = Decimal("1.0") - (position_risk["correlation_risk"] - Decimal("0.5"))
            base_size = base_size * correlation_factor
            logger.info(f"Correlation adjustment for {symbol}: {float(correlation_factor):.2f}x (corr: {float(position_risk['correlation_risk']):.2f})")
        
        # Apply maximum order size limit
        return min(base_size, self.risk_limits["max_order_size"])
    
    def _calculate_order_value(self, order: Union[MarketOrder, LimitOrder]) -> Decimal:
        """Calculate the value of an order in quote currency"""
        amount = Decimal(str(order.amount))
        
        if hasattr(order, 'price') and order.price is not None:
            price = Decimal(str(order.price))
            return amount * price
        else:
            # For market orders without price, we need to estimate
            # In a real implementation, this would fetch the current market price
            # For now, we'll just use a placeholder
            return amount * Decimal("50000")  # Placeholder price
    
    def _calculate_order_risk(self, order: Union[MarketOrder, LimitOrder], account_equity: Decimal) -> Decimal:
        """
        Calculate the risk amount for an order.
        
        For orders with stop loss, risk is calculated as the difference between entry and stop.
        For orders without stop loss, risk is estimated based on volatility.
        """
        order_value = self._calculate_order_value(order)
        
        # If order has risk parameters with stop loss
        if hasattr(order, 'risk_params') and order.risk_params and hasattr(order.risk_params, 'stop_loss_pct'):
            stop_loss_pct = order.risk_params.stop_loss_pct
            if stop_loss_pct:
                return order_value * stop_loss_pct
        
        # Default risk calculation (1% of order value)
        return order_value * Decimal("0.01")
    
    async def update_trade_metrics(self, symbol: str, pnl: Decimal):
        """
        Update trade metrics after a trade is executed or closed.
        
        Args:
            symbol: Trading pair symbol
            pnl: Profit/loss from the trade (positive for profit, negative for loss)
        """
        # Update daily trade count
        self.daily_trades_count[symbol] = self.daily_trades_count.get(symbol, 0) + 1
        
        # Update PnL
        self.daily_pnl[symbol] = self.daily_pnl.get(symbol, Decimal(0)) + pnl
        self.weekly_pnl[symbol] = self.weekly_pnl.get(symbol, Decimal(0)) + pnl
        
        # Log metrics
        logger.info(f"Trade metrics updated for {symbol}: daily_count={self.daily_trades_count[symbol]}, daily_pnl={float(self.daily_pnl[symbol]):.2f}")
        
        # Record metrics if collector is available
        if self.metrics_collector:
            self.metrics_collector.record_counter(f"trades.count.{symbol}", 1)
            self.metrics_collector.record_gauge(f"trades.pnl.daily.{symbol}", float(self.daily_pnl[symbol]))
    
    def register_circuit_breaker(self, symbol: str, threshold: Optional[Decimal] = None, 
                               cooldown_minutes: Optional[int] = None):
        """
        Register a circuit breaker for a symbol.
        
        Args:
            symbol: Trading pair symbol
            threshold: Price move threshold to trigger circuit breaker (default from config)
            cooldown_minutes: Cooldown period in minutes (default from config)
        """
        if threshold is None:
            threshold = risk_config.CIRCUIT_BREAKER_THRESHOLD
        
        if cooldown_minutes is None:
            cooldown_minutes = risk_config.CIRCUIT_BREAKER_COOLDOWN_MINUTES
        
        self.circuit_breakers[symbol] = CircuitBreaker(
            symbol=symbol,
            threshold=threshold,
            cooldown_seconds=cooldown_minutes * 60
        )
        
        logger.info(f"Circuit breaker registered for {symbol} with threshold {float(threshold):.2%}")
    
    async def get_risk_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive risk report.
        
        Returns:
            Dictionary containing risk metrics
        """
        # Get portfolio risk
        portfolio_risk = await self.portfolio_service.calculate_portfolio_risk()
        
        # Get account equity
        account_equity = await self.portfolio_service.get_account_equity()
        
        # Calculate time-based metrics
        daily_pnl_sum = sum(self.daily_pnl.values())
        weekly_pnl_sum = sum(self.weekly_pnl.values())
        
        daily_drawdown = abs(daily_pnl_sum) / account_equity if daily_pnl_sum < 0 else Decimal(0)
        weekly_drawdown = abs(weekly_pnl_sum) / account_equity if weekly_pnl_sum < 0 else Decimal(0)
        
        # Get circuit breaker status
        circuit_breaker_status = {
            symbol: {
                "triggered": cb.is_triggered(),
                "trigger_time": cb.trigger_time,
                "cooldown_remaining": cb.get_cooldown_remaining()
            }
            for symbol, cb in self.circuit_breakers.items()
        }
        
        # Compile report
        return {
            "timestamp": datetime.now().isoformat(),
            "trading_status": {
                "halted": self.trading_halted,
                "halt_reason": self.trading_halt_reason
            },
            "account": {
                "equity": float(account_equity),
                "total_exposure": float(portfolio_risk["total_exposure"]),
                "leverage": float(portfolio_risk["total_exposure"] / account_equity) if account_equity > 0 else 0,
                "position_count": portfolio_risk["position_count"]
            },
            "drawdown": {
                "current": float(portfolio_risk["current_drawdown"]),
                "max": float(portfolio_risk["max_drawdown"]),
                "daily": float(daily_drawdown),
                "weekly": float(weekly_drawdown)
            },
            "risk_metrics": {
                "volatility": float(portfolio_risk["volatility"]),
                "correlation_avg": float(portfolio_risk["correlation_avg"]),
                "concentration_max": float(portfolio_risk["concentration_max"])
            },
            "limits": {
                "portfolio_exposure_pct": float(portfolio_risk["total_exposure"] / self.risk_limits["max_portfolio_exposure"]) if self.risk_limits["max_portfolio_exposure"] > 0 else 0,
                "daily_drawdown_pct": float(daily_drawdown / self.risk_limits["max_daily_drawdown"]) if self.risk_limits["max_daily_drawdown"] > 0 else 0,
                "weekly_drawdown_pct": float(weekly_drawdown / self.risk_limits["max_weekly_drawdown"]) if self.risk_limits["max_weekly_drawdown"] > 0 else 0
            },
            "circuit_breakers": circuit_breaker_status,
            "daily_trades": self.daily_trades_count,
            "daily_pnl": {k: float(v) for k, v in self.daily_pnl.items()},
            "weekly_pnl": {k: float(v) for k, v in self.weekly_pnl.items()}
        }