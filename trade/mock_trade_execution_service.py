"""
Provides a mock trade execution service for testing purposes.
"""

def execute_trade(signal: str):
    """
    Simulates the execution of a trade based on the given signal.

    Args:
        signal (str): The trading signal (e.g., "BUY", "SELL", "HOLD").
    """
    print(f"Received signal: {signal.upper()}")

    if signal.upper() == "BUY":
        print("Mock trade: Executing market BUY order.")
    elif signal.upper() == "SELL":
        print("Mock trade: Executing market SELL order.")
    elif signal.upper() == "HOLD":
        print("Mock trade: No action taken for HOLD signal.")
    else:
        print(f"Mock trade: Unknown signal '{signal}', no action taken.")
        return  # Exit if signal is unknown

    print("Mock trade status: FILLED")

if __name__ == '__main__':
    # Example usage:
    execute_trade("BUY")
    execute_trade("SELL")
    execute_trade("HOLD")
    execute_trade("UNKNOWN_SIGNAL")