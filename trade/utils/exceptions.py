"""
Exchange Exceptions

This module defines exceptions related to exchange operations.
"""

class ExchangeError(Exception):
    """Base class for exchange-related exceptions"""
    pass

class ConnectionError(ExchangeError):
    """Exception raised when connection to exchange fails"""
    pass

class AuthenticationError(ExchangeError):
    """Exception raised when authentication to exchange fails"""
    pass

class OrderError(ExchangeError):
    """Exception raised when order placement fails"""
    pass

class RateLimitError(ExchangeError):
    """Exception raised when rate limit is exceeded"""
    pass

class InsufficientFundsError(ExchangeError):
    """Exception raised when account has insufficient funds"""
    pass

class InvalidOrderError(ExchangeError):
    """Exception raised when order parameters are invalid"""
    pass

class MarketClosedError(ExchangeError):
    """Exception raised when market is closed"""
    pass

class RiskLimitExceededError(ExchangeError):
    """Exception raised when a risk limit is exceeded"""
    pass

class CircuitBreakerTriggeredError(ExchangeError):
    """Exception raised when a circuit breaker is triggered"""
    pass

class TradingHaltedError(ExchangeError):
    """Exception raised when trading is halted"""
    pass