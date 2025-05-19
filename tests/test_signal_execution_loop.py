"""Tests the mock signal-to-execution loop using hardcoded signals."""

import sys
import os

# Add the project root directory to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from strategy.mock_strategy_service import BUY_SIGNAL, SELL_SIGNAL
from trade.mock_trade_execution_service import execute_trade

if __name__ == "__main__":
    print("--- Testing BUY Signal ---")
    execute_trade(BUY_SIGNAL)
    print("\n--- Testing SELL Signal ---")
    execute_trade(SELL_SIGNAL)