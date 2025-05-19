# API Documentation Plan for CryptoBot

**Date:** May 16, 2025
**Project:** CryptoBot
**Objective:** Outline a strategy to generate, consolidate, and make accessible API documentation for all relevant services within the CryptoBot project.

## 1. Introduction

This document outlines the plan for identifying, generating, and consolidating API documentation for the various services within the CryptoBot application. The primary goal is to provide clear, accessible, and comprehensive API references for developers and users. Many services utilize FastAPI, which simplifies documentation generation through OpenAPI.

## 2. Identified API Services and Documentation Sources

The following services have been identified as exposing APIs. For FastAPI-based services, documentation is typically available via `/docs` (Swagger UI) and `/redoc` (ReDoc) endpoints when the service is running.

| Service Name    | Likely Entry Point        | Primary Documentation Method | Notes                                                                 |
| :-------------- | :------------------------ | :--------------------------- | :-------------------------------------------------------------------- |
| `auth`          | [`auth/main.py`](auth/main.py:1)            | FastAPI (OpenAPI)            | Standard `/docs` and `/redoc`.                                        |
| `auth-service`  | [`auth-service/main.py`](auth-service/main.py:1)    | FastAPI (OpenAPI)            | May also have gRPC; focus here is on HTTP/FastAPI docs.             |
| `backtest`      | [`backtest/main.py`](backtest/main.py:1)        | FastAPI (OpenAPI)            | Standard `/docs` and `/redoc`.                                        |
| `data`          | [`data/main.py`](data/main.py:1)            | FastAPI (OpenAPI)            | Standard `/docs` and `/redoc`.                                        |
| `strategy`      | [`strategy/main.py`](strategy/main.py:1)        | FastAPI (OpenAPI)            | Standard `/docs` and `/redoc`.                                        |
| `trade`         | [`trade/main.py`](trade/main.py:1)           | FastAPI (OpenAPI)            | Standard `/docs` and `/redoc`.                                        |
| `api/` (routes) | Integrated into services  | Via Owning Service           | Routes in [`api/`](api/) are assumed to be part of other FastAPI services. |

## 3. Plan for API Documentation Generation and Consolidation

### 3.1. Accessing Live API Documentation

For any running FastAPI-based service, the live, interactive API documentation can be accessed via standard web browser paths:

*   **Swagger UI:** `http://<service-host>:<port>/docs`
*   **ReDoc:** `http://<service-host>:<port>/redoc`

**Example:** If the `trade` service is running locally on port `8001`, its Swagger UI would be at `http://localhost:8001/docs`.

**Presumed Live Documentation Paths (when services are running):**

*   `auth-service`: `http://localhost:<AUTH_PORT>/docs`
*   `backtest-service`: `http://localhost:<BACKTEST_PORT>/docs`
*   `data-service`: `http://localhost:<DATA_PORT>/docs`
*   `strategy-service`: `http://localhost:<STRATEGY_PORT>/docs`
*   `trade-service`: `http://localhost:<TRADE_PORT>/docs`

*(Developers will need to know the specific port each service runs on, as configured in the project.)*

### 3.2. Generating Static OpenAPI Specifications (`openapi.json`)

To have offline versions of the API specifications and to enable further processing (like consolidation), the `openapi.json` file can be fetched from each running FastAPI service.

**Method:**
Use `curl` or a simple script (e.g., Python with `requests`) to fetch the specification:

```bash
# Example for the 'trade' service running on port 8001
curl http://localhost:8001/openapi.json > docs/api/trade-openapi.json
```

This should be done for each service:
*   `auth-openapi.json`
*   `auth-service-openapi.json`
*   `backtest-openapi.json`
*   `data-openapi.json`
*   `strategy-openapi.json`
*   `trade-openapi.json`

**Storage:** All generated `openapi.json` files should be stored in the [`docs/api/`](docs/api/) directory.

### 3.3. Consolidating and Presenting API Documentation

Several approaches can be taken to make the API documentation accessible:

**Option 1: Instructions for Accessing Live Docs (Simplest)**
*   **Description:** Document the standard `/docs` and `/redoc` paths for each service. Users/developers run the services locally (or access deployed instances) to view the documentation.
*   **Pros:** Always up-to-date with the running code. No extra generation step.
*   **Cons:** Requires services to be running. Documentation is fragmented across services.

**Option 2: Generating and Hosting Individual Static HTML Docs**
*   **Description:** Use a tool like `redoc-cli` to convert each service's `openapi.json` into a standalone static HTML file.
    ```bash
    # Example for trade service
    npx redoc-cli build docs/api/trade-openapi.json --output docs/api/trade-docs.html
    ```
*   These HTML files (`auth-docs.html`, `trade-docs.html`, etc.) would be stored in [`docs/api/`](docs/api/) and can be viewed directly in a browser.
*   **Pros:** Offline access. No need for services to be running to view docs.
*   **Cons:** Still somewhat fragmented, though centrally stored. Requires a generation step.

**Option 3: Unified API Documentation Portal (Recommended)**
*   **Description:** Use a specialized tool to combine the individual `openapi.json` files into a single, unified documentation portal or a set of linked static HTML pages. This provides a much better user experience with features like cross-service search (if supported by the tool).
*   **Recommended Tool:** **Redocly CLI**
    *   Redocly CLI can bundle multiple OpenAPI specifications into a single, well-organized portal. It offers features like sidebar navigation for different services, search, and customizable themes.
    *   Example (conceptual command, actual usage may vary):
        ```bash
        npx @redocly/cli bundle auth-openapi.json trade-openapi.json ... -o docs/api/index.html --title "CryptoBot API Documentation"
        ```
*   **Alternative Tools:** SwaggerHub (cloud-based), Docusaurus with OpenAPI plugins, or custom scripting to generate a main index linking to individual static HTML docs (from Option 2).
*   **Pros:** Centralized, searchable, and user-friendly documentation. Offline access.
*   **Cons:** Requires a more involved setup and generation script.
*   **Storage:** All generated portal files (HTML, JS, CSS) should be stored in [`docs/api/`](docs/api/).

## 4. Recommended Approach for Users/Developers

A hybrid approach is recommended:

1.  **For the most up-to-date, interactive documentation:** Developers should run the required services locally and access their respective `/docs` or `/redoc` endpoints.
2.  **For offline reference and a consolidated view:** A unified static documentation portal (Option 3 above, using Redocly CLI) should be generated periodically (e.g., as part of a documentation build process or manually after significant API changes) and made available in the [`docs/api/`](docs/api/) directory. This portal would serve as the primary reference point.

## 5. Storage of Generated Artifacts

All generated static API documentation artifacts, including:
*   Individual `openapi.json` files (e.g., [`docs/api/trade-openapi.json`](docs/api/trade-openapi.json))
*   Individual static HTML documentation files (if Option 2 is partially used, e.g., [`docs/api/trade-docs.html`](docs/api/trade-docs.html))
*   Consolidated API documentation portal files (e.g., [`docs/api/index.html`](docs/api/index.html) and related assets)

...will be stored in the **`docs/api/`** directory within the project.

## 6. Process Flow Diagram (Mermaid)

```mermaid
graph TD
    A[FastAPI Service: auth] -- /openapi.json --> F1[auth-openapi.json];
    B[FastAPI Service: backtest] -- /openapi.json --> F2[backtest-openapi.json];
    C[FastAPI Service: data] -- /openapi.json --> F3[data-openapi.json];
    D[FastAPI Service: strategy] -- /openapi.json --> F4[strategy-openapi.json];
    E[FastAPI Service: trade] -- /openapi.json --> F5[trade-openapi.json];
    X[FastAPI Service: auth-service] -- /openapi.json --> F6[auth-service-openapi.json];

    subgraph Generation [Static Specification Generation]
        direction LR
        F1; F2; F3; F4; F5; F6;
    end

    Generation --> G{Consolidation Strategy};

    subgraph Consolidation Options
        direction TB
        G -- Option 1 --> H1[Live Docs: /docs, /redoc per service];
        G -- Option 2 --> H2[Individual Static HTMLs in docs/api];
        G -- Option 3 (Recommended) --> H3[Unified Portal (e.g., Redocly CLI) in docs/api];
    end

    H3 --> I[Stored in docs/api/];
    H2 --> I;
    F1 --> J[Stored in docs/api/];
    F2 --> J;
    F3 --> J;
    F4 --> J;
    F5 --> J;
    F6 --> J;

    style Generation fill:#f9f,stroke:#333,stroke-width:2px
    style Consolidation fill:#ccf,stroke:#333,stroke-width:2px
```

This plan provides a clear path to establishing comprehensive API documentation for the CryptoBot project.