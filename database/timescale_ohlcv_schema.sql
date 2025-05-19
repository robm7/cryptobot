-- Ensure the TimescaleDB extension is enabled in your database:
-- CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Drop table if it exists to ensure a clean setup (optional, for development)
DROP TABLE IF EXISTS ohlcv_data CASCADE;

-- Create the OHLCV data table
CREATE TABLE ohlcv_data (
    timestamp TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(30) NOT NULL,     -- e.g., BTC/USDT
    timeframe VARCHAR(10) NOT NULL,  -- e.g., 1m, 5m, 1h, 1d
    open NUMERIC NOT NULL,
    high NUMERIC NOT NULL,
    low NUMERIC NOT NULL,
    close NUMERIC NOT NULL,
    volume NUMERIC NOT NULL
);

-- Create a TimescaleDB hypertable, partitioned by time (timestamp)
-- Optionally, add space partitioning on 'symbol' or 'exchange' if you have many of them
-- and queries often filter by these columns.
-- For example, partitioning by symbol if you have hundreds/thousands of symbols:
-- SELECT create_hypertable('ohlcv_data', 'timestamp', partitioning_column => 'symbol', number_partitions => 10);
-- Or by exchange if you have many exchanges:
-- SELECT create_hypertable('ohlcv_data', 'timestamp', partitioning_column => 'exchange', number_partitions => 4);
-- If no space partitioning is needed, or unsure, start with time partitioning only:
SELECT create_hypertable('ohlcv_data', 'timestamp');

-- Create indexes for common query patterns
-- TimescaleDB automatically creates an index on the time dimension ('timestamp')
-- Index for filtering by exchange, symbol, and timeframe, then sorting by time (common for charts)
CREATE INDEX IF NOT EXISTS idx_ohlcv_exchange_symbol_timeframe_timestamp 
    ON ohlcv_data (exchange, symbol, timeframe, timestamp DESC);

-- Index for queries filtering by symbol and timeframe (e.g., for a specific chart)
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timeframe_timestamp 
    ON ohlcv_data (symbol, timeframe, timestamp DESC);

-- Optional: Index for just symbol and timestamp if often querying all timeframes for a symbol
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timestamp 
    ON ohlcv_data (symbol, timestamp DESC);

-- Optional: Consider enabling compression for older data to save space
-- This should be done after some data is ingested and you understand access patterns.
-- Example: Compress data older than 7 days, segment by symbol and order by time for better compression ratios.
-- ALTER TABLE ohlcv_data SET (timescaledb.compress, timescaledb.compress_segmentby = 'symbol', timescaledb.compress_orderby = 'timestamp DESC');
-- SELECT add_compression_policy('ohlcv_data', compress_after => INTERVAL '7 days');

-- Optional: Data retention policy to drop very old data
-- Example: Drop data older than 2 years
-- SELECT add_retention_policy('ohlcv_data', drop_after => INTERVAL '2 years');

COMMENT ON TABLE ohlcv_data IS 'Stores OHLCV (Open, High, Low, Close, Volume) time-series data for various exchanges, symbols, and timeframes.';
COMMENT ON COLUMN ohlcv_data.timestamp IS 'The start timestamp of the OHLCV candle (UTC).';
COMMENT ON COLUMN ohlcv_data.exchange IS 'Name of the exchange (e.g., binance, coinbasepro).';
COMMENT ON COLUMN ohlcv_data.symbol IS 'Trading symbol or pair (e.g., BTC/USDT).';
COMMENT ON COLUMN ohlcv_data.timeframe IS 'Candle timeframe (e.g., 1m, 5m, 1h, 1d).';
COMMENT ON COLUMN ohlcv_data.open IS 'Opening price for the candle.';
COMMENT ON COLUMN ohlcv_data.high IS 'Highest price during the candle.';
COMMENT ON COLUMN ohlcv_data.low IS 'Lowest price during the candle.';
COMMENT ON COLUMN ohlcv_data.close IS 'Closing price for the candle.';
COMMENT ON COLUMN ohlcv_data.volume IS 'Trading volume during the candle.';