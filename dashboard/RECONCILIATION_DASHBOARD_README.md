# Reconciliation Dashboard

The Reconciliation Dashboard provides a user-friendly interface for monitoring and analyzing order reconciliation results. It allows users to visualize reconciliation data, identify discrepancies between local records and exchange data, and trigger manual reconciliation runs.

## Features

### Summary Statistics

The dashboard displays key summary statistics for the selected time period:

- **Total Orders**: The total number of orders processed during reconciliation
- **Mismatched Orders**: The number of orders with discrepancies
- **Average Mismatch Rate**: The percentage of orders with discrepancies
- **Alerts Triggered**: The number of reconciliation runs that triggered alerts

### Visualizations

The dashboard includes two main visualizations:

1. **Reconciliation History Chart**: Shows the trend of total orders, mismatched orders, and mismatch rate over time
2. **Mismatch Distribution Chart**: Shows the breakdown of matched orders, missing orders, extra orders, and other mismatches for each reconciliation run

### Reports Table

The dashboard displays a table of reconciliation reports with key information:

- Timestamp
- Total Orders
- Matched Orders
- Mismatched Orders
- Mismatch Rate
- Alert Status

Users can click on a report to view detailed information about that specific reconciliation run.

### Report Details

When a report is selected, the dashboard displays detailed information about the reconciliation run:

- General Information (timestamp, time period, total orders, mismatch rate)
- Mismatch Breakdown (matched orders, mismatched orders, missing orders, extra orders)

### Manual Reconciliation

Users can trigger a manual reconciliation run by clicking the "Run Reconciliation Now" button. This will initiate a reconciliation job and update the dashboard with the results when complete.

## Integration with Backend API

The Reconciliation Dashboard integrates with the backend API endpoints provided by the reconciliation service:

- `GET /reconciliation/summary`: Retrieves summary statistics for a specified time period
- `GET /reconciliation/reports`: Retrieves detailed reconciliation reports with optional filtering
- `POST /reconciliation/run`: Triggers a manual reconciliation run
- `GET /reconciliation/status`: Retrieves the current status of the reconciliation job

## Usage

### Accessing the Dashboard

The Reconciliation Dashboard can be accessed from the main navigation menu by clicking on "Reconciliation".

### Filtering Data

Users can filter the data displayed on the dashboard by selecting a time period from the dropdown menu:

- Last 24 Hours
- Last 7 Days
- Last 30 Days
- Last 90 Days

### Running Reconciliation

To run a manual reconciliation:

1. Click the "Run Reconciliation Now" button
2. Wait for the reconciliation job to complete
3. The dashboard will automatically update with the new results

### Viewing Report Details

To view detailed information about a specific reconciliation run:

1. Locate the report in the Reports Table
2. Click on the report row
3. The Report Details section will update with information about the selected report

## Implementation Details

The Reconciliation Dashboard is implemented using:

- **Next.js**: For the page structure and routing
- **React**: For the component-based UI
- **D3.js**: For the interactive data visualizations
- **Axios**: For API communication

### Components

- `reconciliation.js`: The main page component
- `ReconciliationChart.js`: Component for the reconciliation history chart
- `MismatchChart.js`: Component for the mismatch distribution chart

### Data Flow

1. The dashboard fetches data from the backend API endpoints
2. The data is processed and transformed for display
3. The charts and tables are rendered with the processed data
4. User interactions (filtering, selecting reports, running reconciliation) trigger updates to the displayed data

## Future Enhancements

Potential future enhancements for the Reconciliation Dashboard:

1. **Real-time Updates**: Implement WebSocket connections for real-time updates during reconciliation runs
2. **Advanced Filtering**: Add more filtering options (exchange, symbol, etc.)
3. **Export Functionality**: Allow users to export reconciliation reports in various formats (CSV, PDF, etc.)
4. **Detailed Mismatch Analysis**: Provide more detailed analysis of mismatches, including specific order IDs and discrepancy types
5. **Automated Alerts**: Configure alert thresholds and notification channels directly from the dashboard