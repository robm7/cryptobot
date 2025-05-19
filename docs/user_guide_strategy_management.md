## 5. Strategy Management

The CryptoBot platform allows you to create, manage, and deploy various trading strategies. This section explains how to interact with the strategy management features.

*(This guide assumes interaction via an API client or a UI that consumes the strategy management API. Specific UI elements would be described if a UI for direct strategy management exists.)*

### Listing Strategies

You can retrieve a list of all available trading strategies.

*   **How to List**: Make a `GET` request to the `/api/strategies/` endpoint.
*   **Filtering**:
    *   By default, this usually returns only **active** strategies.
    *   You can often include inactive strategies by adding a query parameter (e.g., `?active_only=false`).
*   **Information Displayed**: The list provides key information for each strategy: ID, Name, Current Version, Active Status.

### Viewing Strategy Details

To get comprehensive details about a specific strategy, including its parameters and version history:

*   **How to View**: Make a `GET` request to `/api/strategies/{strategy_id}`.
*   **Information Displayed**: Includes ID, Name, Description, Parameters, Active Status, Current Version, and a list of all historical versions with their parameters and creation timestamps.

### Creating a New Strategy

Define and save new trading strategies.

*   **How to Create**: Make a `POST` request to `/api/strategies/` with a JSON payload:
    *   `name` (string, required): A unique name.
    *   `description` (string, optional): A brief description.
    *   `parameters` (object, required): Initial parameters (e.g., `{"rsi_period": 14}`).
    *   `is_active` (boolean, optional, defaults to `true`).
*   **Outcome**: Returns the new strategy's details, including ID and initial version (version 1). An initial version record is automatically created.

### Updating an Existing Strategy

Modify an existing strategy's details.

*   **How to Update**: Make a `PUT` request to `/api/strategies/{strategy_id}` with a JSON payload of fields to change.
    *   `name`, `description`, `is_active` update the current version.
    *   Changing `parameters` creates a **new version** of the strategy, incrementing the main version number.
*   **Outcome**: Returns the updated strategy details, including the current (possibly new) version.

### Deleting a Strategy

Permanently remove a strategy if no longer needed (typically admin-restricted).

*   **How to Delete**: Make a `DELETE` request to `/api/strategies/{strategy_id}`.
*   **Outcome**: The strategy and all its versions are removed. Usually returns a `204 No Content` status.
*   **Caution**: Deletion is permanent.

### Activating and Deactivating Strategies

Toggle strategies between active (eligible for trading) and inactive states.

*   **How to Activate**: `POST` request to `/api/strategies/{strategy_id}/activate`. Sets `is_active` to `true`.
*   **How to Deactivate**: `POST` request to `/api/strategies/{strategy_id}/deactivate`. Sets `is_active` to `false`.
*   **Outcome**: Both return the updated strategy details.

### Managing Strategy Versions

Parameter changes automatically create new versions.

*   **Viewing Versions**: Strategy details include historical versions. Direct fetch via `GET /api/strategies/{strategy_id}/versions`.
*   **Reverting (Conceptual)**: To use parameters from an older version, fetch them, then use the "Update Strategy" endpoint to apply these parameters. This creates a new version effectively copying the old one.

Proper strategy management is key to organizing and refining your trading approaches.