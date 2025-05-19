# Enhanced Position Sizing System

This document describes the enhanced position sizing system implemented for the crypto trading bot.

## Overview

The enhanced position sizing system provides more sophisticated risk management capabilities:

1. **Dynamic Position Sizing Based on Volatility**
   - Adjusts position sizes based on market volatility
   - Higher volatility assets get smaller position sizes
   - Uses a non-linear scaling algorithm to avoid too drastic reductions

2. **Risk Per Trade Calculations**
   - Customizable risk tolerance per trade
   - Considers account equity when calculating position sizes
   - Supports stop-loss based position sizing

3. **Maximum Drawdown Controls**
   - Progressively reduces position sizes as drawdown increases
   - Implements trading halt mechanisms for critical drawdown levels
   - Provides different levels of drawdown response (moderate, severe, critical)

## Implementation Details

### Dynamic Volatility-Based Position Sizing

The system compares an asset's volatility against a baseline value (default: 50%). When volatility exceeds this baseline, position sizes are reduced according to a non-linear scaling algorithm:

```python
if volatility_decimal > cls.VOLATILITY_BASELINE:
    # Calculate how much volatility exceeds baseline (as a ratio)
    excess_volatility_ratio = (volatility_decimal / cls.VOLATILITY_BASELINE) - Decimal('1.0')
    
    # Apply non-linear scaling (square root) to avoid too drastic reductions
    adjustment_factor = Decimal('1.0') - (cls.VOLATILITY_MAX_ADJUSTMENT * 
                                        (Decimal(str(np.sqrt(float(excess_volatility_ratio)))))
                                       )
    
    # Ensure adjustment doesn't go below minimum threshold (25% of original size)
    adjustment_factor = max(adjustment_factor, Decimal('0.25'))
    
    # Apply adjustment
    base_size = base_size * adjustment_factor
```

This approach ensures that:
- Position sizes decrease as volatility increases
- The reduction is not linear, avoiding excessive position size reduction for very volatile assets
- There's a minimum position size threshold (25% of normal size)

### Risk Per Trade Calculations

The system allows for customizable risk per trade settings:

```python
# Use custom risk tolerance if provided, otherwise use default
risk_per_trade = risk_tolerance if risk_tolerance is not None else cls.RISK_PER_TRADE

# Base position size calculation
base_size = account_equity * risk_per_trade
```

This enables:
- Different risk levels for different strategies or market conditions
- Adjusting risk based on account size
- Incorporating stop-loss levels into position sizing

### Maximum Drawdown Controls

The system implements progressive drawdown controls:

```python
if drawdown_abs < cls.MAX_DRAWDOWN_THRESHOLD:
    # Scale down linearly between 5% and MAX_DRAWDOWN_THRESHOLD
    severity = (drawdown_abs - Decimal('0.05')) / (cls.MAX_DRAWDOWN_THRESHOLD - Decimal('0.05'))
    reduction_factor = Decimal('1.0') - (severity * Decimal('0.5') * cls.DRAWDOWN_SCALING_FACTOR)
    adjusted_size = position_size * reduction_factor
    return adjusted_size
    
elif drawdown_abs < cls.CRITICAL_DRAWDOWN_THRESHOLD:
    # Severe drawdown - more aggressive reduction (25% of normal size)
    return position_size * Decimal('0.25')
    
else:
    # Critical drawdown - minimal position size (10% of normal) or consider halting trading
    return position_size * Decimal('0.1')
```

This provides:
- Gradual position size reduction as drawdown increases
- Different thresholds for different levels of drawdown severity
- Trading halt mechanisms for critical drawdown levels

## Integration with Portfolio Management

The enhanced position sizing system integrates with the portfolio management system:

- The `PortfolioService` tracks account equity and calculates drawdown metrics
- Position sizing takes into account portfolio-level risk metrics
- Correlation and concentration risk are considered in order validation

## Configuration

The system is highly configurable through class constants in the `RiskService` class:

```python
# Volatility scaling factors
VOLATILITY_SCALING_ENABLED = True
VOLATILITY_BASELINE = Decimal('0.50')  # Baseline volatility (considered "normal")
VOLATILITY_MAX_ADJUSTMENT = Decimal('0.75')  # Maximum reduction due to volatility (75%)

# Drawdown control settings
DRAWDOWN_CONTROL_ENABLED = True
DRAWDOWN_SCALING_FACTOR = Decimal('2.0')  # How aggressively to scale down on drawdown
MAX_DRAWDOWN_THRESHOLD = Decimal('0.15')  # 15% max drawdown threshold
CRITICAL_DRAWDOWN_THRESHOLD = Decimal('0.25')  # 25% critical drawdown threshold
```

These settings can be adjusted based on risk preferences and market conditions.