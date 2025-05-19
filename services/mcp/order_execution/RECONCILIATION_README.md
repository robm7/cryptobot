# Order Reconciliation Reporting

This module provides reporting capabilities for the order reconciliation system. It allows you to generate reports on order reconciliation results, view historical reconciliation data, and trigger manual reconciliation runs.

## Components

### Reconciliation Job

The `ReconciliationJob` class in `reconciliation_job.py` is responsible for:

- Running scheduled reconciliation processes
- Comparing local order records with exchange data
- Generating reconciliation reports
- Alerting on discrepancies

### Reporting Integration

The reconciliation system is now integrated with the reporting system:

- The `ReportingInterface` has been extended with a `generate_reconciliation_report` method
- The `BasicReporter` implementation provides reconciliation reporting capabilities
- Reports can be filtered by date range, exchange, symbol, etc.

### API Endpoints

The following API endpoints are available for reconciliation reporting:

- `GET /reconciliation/reports` - Get reconciliation reports with optional filtering
- `POST /reconciliation/run` - Run reconciliation job manually
- `GET /reconciliation/status` - Get reconciliation job status
- `GET /reconciliation/summary` - Get reconciliation summary for a specified number of days

## Usage

### Running the API

To run the MCP API server which includes the reconciliation endpoints:

```bash
cd services/mcp
python api_app.py
```

This will start the FastAPI application on port 8000 (or the port specified in the `MCP_API_PORT` environment variable).

### Accessing the API Documentation

Once the API server is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Example API Requests

#### Get Reconciliation Reports

```bash
curl -X GET "http://localhost:8000/reconciliation/reports" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Run Reconciliation Manually

```bash
curl -X POST "http://localhost:8000/reconciliation/run" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Get Reconciliation Status

```bash
curl -X GET "http://localhost:8000/reconciliation/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Get Reconciliation Summary

```bash
curl -X GET "http://localhost:8000/reconciliation/summary?days=7" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Integration with Main Application

The reconciliation reporting functionality is designed to be integrated with the main Cryptobot application. The FastAPI application in `api_app.py` can be:

1. Run as a standalone service
2. Mounted as a sub-application in the main Flask application
3. Used as a reference for implementing similar functionality in the main application

## Future Enhancements

Potential future enhancements for the reconciliation reporting system:

1. Dashboard UI for visualizing reconciliation results
2. More sophisticated matching algorithms for reconciliation
3. Integration with notification systems for alerts
4. Enhanced filtering and search capabilities for reports
5. Export functionality for reconciliation reports (CSV, PDF, etc.)