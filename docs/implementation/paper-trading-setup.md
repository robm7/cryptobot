# Paper Trading Setup Guide

## Kraken Paper Trading Configuration

1. Create paper trading account:
   - Visit https://demo-futures.kraken.com
   - Register for a demo account

2. Generate API keys:
   - Go to Settings → API
   - Create new API key with trading permissions
   - Note: Never share your API secret

3. Set environment variables:
```bash
export KRAKEN_PAPER_API_KEY=your_api_key_here
export KRAKEN_PAPER_API_SECRET=your_api_secret_here
```

4. Verify setup:
```bash
python -m pytest test_kraken_isolated.py -v
```

## Testing Without Paper Trading

Use the mock test instead:
```bash
python -m pytest test_kraken_mock.py -v
```

## Troubleshooting

- If tests skip: Verify environment variables are set
- If connection fails: Check API key permissions
- For other issues: See TESTING.md