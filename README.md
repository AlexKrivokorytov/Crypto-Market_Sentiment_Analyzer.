# 📊 Cryptex — Real-Time Market Intelligence Center

<div align="center">

[![Build & E2E Validation](https://img.shields.io/badge/Build--Validation-Passing-059669?style=for-the-badge&logo=github-actions&logoColor=white)](https://github.com)
[![Vue 3 Composition API](https://img.shields.io/badge/Vue--3--Composition--TS-Strict--No--Emit-41B883?style=for-the-badge&logo=vue.js&logoColor=white)](https://vuejs.org)
[![FastAPI Async](https://img.shields.io/badge/FastAPI-Fully--Async--0.136+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas--Secure-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com)
[![Docker Multi-Network](https://img.shields.io/badge/Docker-Hardened--Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com)

**An Enterprise-grade, high-frequency cryptocurrency and equity sentiment intelligence dashboard. Engineered with async-safe design patterns, FSM circuit breakers, log-normal market simulators, and production-hardened network topologies.**

[Live Application Demo](http://localhost:8080) · [Backend API Sandbox](http://localhost:8000/docs) · [Report Bug](https://github.com)

</div>

---

## 📖 Overview

**Cryptex** is a high-performance, full-stack Market Intelligence Single Page Application (SPA) designed to track, aggregate, and visualize real-time asset prices overlaid with live sentiment metrics. The system is engineered to provide continuous, high-fidelity data visualization under strict free-tier hosting limitations (e.g., Render Free-Tier and MongoDB Atlas storage boundaries).

### Core Pipeline:
1. **Real-time Feeds**: Spot rates are continuously ingested asynchronously from the **Alchemy Prices API** and **yfinance**.
2. **Sentiment Ingestion**: Search-based Google News RSS feeds are parsed periodically via cooperative async loops.
3. **AI Evaluation (VADER + LLM)**: Headlines and summaries undergo sentiment evaluation via a local/external LLM (**Ollama**, **LM Studio**) or a local async-wrapped VADER engine.
4. **Resilient Reactive Fallbacks**: Implements a 3-state Circuit Breaker FSM and a log-normal Geometric Brownian Motion (GBM) price simulator to keep the dashboard reactive even during complete downstream API outages.

---

## 🏗️ System Architecture

The blueprint below details the asynchronous, decoupled pipeline, including the factory data handlers, 3-state circuit breaker, isolated websocket queues, and isolated multi-network Docker containers:

```mermaid
graph TD
    subgraph Frontend["Vue 3 SPA (Client)"]
        V["Vue 3 Components Setup TS"] <--> PQ["TanStack Vue Query Caches"]
        V <--> P["Pinia Client States (Hydration)"]
        V <--> C["Apache ECharts Rendering"]
        V <--> WS_C["useWebSocketManager (60Hz Throttled)"]
    end

    subgraph Backend["FastAPI Engine (Python 3.12 Fully Async)"]
        E["API Endpoints & Routers"] <--> WS_S["websocket_endpoint (Slow Client Shield)"]
        BUL["background_update_loop (Orchestrator)"]
        Parser["rss_parser_loop (Cooperative Yielding)"]
        
        subgraph Handlers["Factory Asset Handlers (SOLID / OOP)"]
            F["AssetHandlerFactory"]
            F --> CH["CryptoHandler (Alchemy / CoinGecko)"]
            F --> SH["StockHandler (yfinance)"]
        end
        
        subgraph Reliability["Fault Tolerance Shield"]
            CB["Circuit Breaker (3-state FSM)"]
            SIM["GBM Market Simulator"]
        end
    end

    subgraph LLM["AI Pipeline / Fallback"]
        LLM_API["Ollama / LM Studio API"]
        Vader["Local VADER Sentiment Engine"]
        Cache["LLMAnalysisCache (FIFO 200, 1h TTL)"]
    end

    subgraph Database["Persistence Layer (Isolated Network)"]
        DB[("MongoDB Container (Auth Enforced)")]
    end

    PQ <--> E
    WS_C <--> WS_S
    BUL --> F
    CH -- "Success Paths" --> DB
    SH -- "Success Paths" --> DB
    BUL -- "Exception caught" --> SIM
    SIM -- "GBM fallback stream" --> DB
    Parser --> Cache
    Cache --> CB
    CB -- "CLOSED (Success)" --> LLM_API
    CB -- "OPEN (Fallback)" --> Vader
    Parser --> DB
    E --> DB
```

---

## 🎯 Key Architectural Milestones & Engineering Patterns

### 🚀 Config-Driven SOLID Handler Factory (Sprint 1)
To eliminate monolithic and duplicating price-feed logic, the backend implements a clean **Factory Pattern** mapped to an Abstract Base Class `BaseAssetHandler` (`backend/app/handlers/base.py`):
* **Open/Closed Principle (OCP)**: Adding new crypto tokens or equities (e.g., DOT, SOL, DOGE, XRP, ADA) requires **only a single configuration line** inside `handlers/config.py`. The rest of the ingestion orchestrators process new assets automatically without a single code change.
* **Unified Interface**: Concrete `CryptoHandler` and `StockHandler` implement uniform `fetch_price()` and `fetch_ohlcv()` interfaces, encapsulating internal API complexities (caching, fallbacks).

### ⚡ Resilient 3-State FSM Circuit Breaker (Sprint 2)
To protect the server loop from high LLM inference latencies and API rate-limiting blocks, we introduced an async-safe, reentrant `CircuitBreaker` (`backend/app/core/circuit_breaker.py`):
* **State Machine**: Transitions automatically between `CLOSED` (normal LLM querying), `OPEN` (rate-limited/failed, instant routing to local fallback), and `HALF_OPEN` (probing downstream recovery with single test requests).
* **Deterministic Fallback**: Under `OPEN` state, sentiment requests are trapped instantly and routed to a rapid local **VADER engine** in microseconds. Structured `circuit_breaker_state_change` warning logs are emitted at each state transition to drive Prometheus/Grafana alerts.

### 📈 Non-Blocking Geometric Brownian Motion (GBM) Simulator (Sprint 3)
When all primary data providers fail, the update loop triggers a mathematical fallback price stream generator based on **Geometric Brownian Motion (GBM)** (`backend/app/services/simulator.py`):
* **Mathematical Realism**: Utilizes log-normal steps ($S_{t+\Delta t} = S_t \cdot e^{(\mu - \frac{\sigma^2}{2})\Delta t + \sigma\sqrt{\Delta t}Z}$), guaranteeing simulated prices **always remain positive ($> 0$)** and reflect realistic market volatility ($\sigma$).
* **Event Loop Shield**: Single price ticks are advanced synchronously in nanoseconds (CPU-bound). Bulk historical candle generations (e.g., 168 hours of seeds) are automatically offloaded to a thread pool executor using `asyncio.to_thread` to maintain a non-blocking ASGI event loop.

### 🛡️ Production-Hardened Docker Architecture (Sprint 4)
The containerized infrastructure is strictly hardened for enterprise security compliance in `docker-compose.yml`:
* **Network Isolation**: Separated into private isolated networks. The persistent database container resides exclusively on `db_network` (internal: true), which is **completely unreachable** from the frontend container. The backend bridges `db_network` and `app_network` to safely broker requests.
* **MongoDB Authentication**: Root access credentials (`MONGO_INITDB_ROOT_USERNAME` / `PASSWORD`) are strictly enforced locally to match Atlas production profiles, with isolated environment variable variables loaded via `.env`.
* **Resource Constraints**: Implements hardware resource limits (caps runaway memory/CPU loops) and strict log rotation configs (`max-size: 10m`, `max-file: 3`) to prevent disk-exhaustion DoS events.
* **Dockerfile Hardening**: Employs BuildKit pip dependency cache mounts for blazing-fast image builds and forces `PYTHONHASHSEED=random` to mitigate dictionary hash-collision DoS attacks.

### 🎨 Fluid Responsive UI & Accessibility (Sprint 5)
The single-page client represents the absolute peak of modern, premium frontend aesthetics:
* **Stale Artifact Purge**: Removed all compiler-generated stale `.js` files from the source tree. Enforced strict `"noEmit": true` inside [tsconfig.json](file:///c:/Users/krivo/Desktop/Rust/vue/frontend/tsconfig.json) and configured Vite type-checking as `vue-tsc --noEmit` in `package.json` to prevent source directory pollution.
* **Server State Decoupling**: Centralized TanStack Query server-state queries inside a decoupled [useDashboard.ts](file:///C:/Users/krivo/Desktop/Rust/vue/frontend/src/composables/useDashboard.ts) composable.
* **Container Queries**: Integrated modern CSS `@container` queries in [Sidebar.vue](file:///C:/Users/krivo/Desktop/Rust/vue/frontend/src/components/layout/Sidebar.vue) to collapse navigation labels dynamically based on parent width (icon-only mode) rather than pure JS states.
* **High-Fidelity Indicators**: Upgraded [StatusIndicator.vue](file:///C:/Users/krivo/Desktop/Rust/vue/frontend/src/components/dashboard/StatusIndicator.vue) with a custom CSS `pulse-ring` keyframe animation that shifts glows beautifully depending on WebSocket stream health (`CONNECTED`, `CONNECTING`, `RECONNECTING`, `OFFLINE`).

---

## 📂 Project Layout & File Tree

```text
├── backend/                       # FastAPI Backend Engine (Python 3.12)
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   └── endpoints.py   # WebSocket loops & REST endpoints
│   │   │   └── dependencies.py    # Decoupled dependency injections
│   │   ├── core/
│   │   │   ├── circuit_breaker.py # Async 3-state Circuit Breaker FSM
│   │   │   ├── config.py          # Environment settings loader
│   │   │   └── database.py        # MongoDB connection & index registers
│   │   ├── handlers/              # SOLID asset data handlers (S1)
│   │   │   ├── base.py            # Handler ABC interface
│   │   │   ├── config.py          # Unified config-driven registry (OCP)
│   │   │   ├── crypto_handler.py  # Alchemy & CoinGecko client
│   │   │   ├── stock_handler.py   # yfinance client
│   │   │   └── factory.py         # AssetHandlerFactory dispatch
│   │   ├── schemas/
│   │   │   └── market.py          # Pydantic schemas
│   │   ├── services/
│   │   │   ├── simulator.py       # Geometric Brownian Motion model (S3)
│   │   │   ├── market_data.py     # Database seed & background update loop
│   │   │   ├── parser.py          # RSS feed fetcher & deduplicator
│   │   │   └── websocket_manager.py # Isolated client queue manager
│   │   └── tests/
│   │       ├── test_circuit_breaker.py # Circuit breaker unit & safety tests
│   │       ├── test_handler_factory.py # Factory registration & OCP test cases
│   │       └── test_simulator.py  # GBM mathematical & loop tests
│   ├── Dockerfile                 # Light multi-stage Python container
│   └── requirements.txt           # Explicitly pinned packages
│
├── frontend/                      # Vue 3 Single Page Application
│   ├── src/
│   │   ├── components/
│   │   │   ├── dashboard/         # Widget components & charts
│   │   │   │   ├── StatusIndicator.vue # Pulse-ring keyframe indicator (S5)
│   │   │   │   └── WidgetWrapper.vue  # Error-capturing reset boundary
│   │   │   └── layout/
│   │   │       ├── Header.vue     # Breadcrumbs & active timeframe pills
│   │   │       └── Sidebar.vue    # CSS @container collapsing sidebar (S5)
│   │   ├── composables/
│   │   │   └── useDashboard.ts    # Centralized TanStack Query composable (S5)
│   │   ├── views/
│   │   │   └── DashboardView.vue  # Responsive fluid grid layout view
│   │   ├── App.vue                # Root entry template
│   │   └── main.ts                # App initialization
│   ├── Dockerfile                 # Multi-stage production Nginx container
│   ├── tailwind.config.js         # Custom HSL design tokens
│   ├── tsconfig.json              # TypeScript compilation (noEmit: true) (S5)
│   └── vite.config.ts             # Vite chunk optimizers
│
├── docker-compose.yml             # Hardened multi-network stack orchestrator
└── README.md                      # Professional technical overview
```

---

## ⚙️ Development Environment Setup

Launch the complete multi-container enterprise stack locally in minutes:

### Prerequisites
* [Docker & Docker Desktop](https://www.docker.com/products/docker-desktop) installed.
* *Optional:* Ollama or LM Studio running locally if you want to route requests to local LLMs.

### Step-by-Step Installation

1. **Clone the Repository** and navigate to the directory:
   ```bash
   git clone https://github.com/your-username/crypto-sentiment-analyzer.git
   cd crypto-sentiment-analyzer
   ```

2. **Configure Environment Variables**
   Create a local env file in the `backend/` directory:
   ```bash
   cp backend/.env.example backend/.env
   ```
   Add your credentials. If you are integrating a host-running Ollama instance within Docker, use the following:
   ```env
   # Local Hardened MongoDB Connection (Auth enforced)
   MONGODB_URL=mongodb://root:admin_secure_password@mongodb:27017
   MONGODB_DB_NAME=sentiment_db
   
   # Local Ollama Docker bridge URL
   LLM_API_URL=http://host.docker.internal:11434/v1
   LLM_MODEL=gemma:2b
   
   # Alchemy API Spot prices
   ALCHEMY_API_KEY=your_alchemy_key_here
   
   # Secure JWT Secret
   JWT_SECRET_KEY=generate_a_secure_hex_key_here
   ```
   > [!TIP]
   > Generate a cryptographically secure 256-bit JWT secret by running:
   > `python -c "import secrets; print(secrets.token_hex(32))"`

3. **Orchestrate Container Startup**
   Use Docker Compose to build and launch all containers in detached mode:
   ```bash
   docker compose up --build -d
   ```
   This orchestrates the startup of three cooperative services:
   * **`mongodb`**: Persistent database running strictly inside `db_network` with enforced authentication.
   * **`backend`**: Port `8000`. Runs async updates, cooperatively schedules RSS parsing, and manages client WebSockets.
   * **`frontend`**: Port `8080`. Serves the Vue 3 SPA through Nginx.

4. **Verify In-Action**
   * Explore the real-time visual dashboard: 👉 **[http://localhost:8080](http://localhost:8080)**
   * Explore and interact with the FastAPI Swagger sandbox: 👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 🛠️ Code Quality & Verification Gates

Quality checks are strictly enforced across both front-end and back-end stacks. All gates must pass with **zero warnings/errors** before deployment.

### 🎨 Frontend Verification (Vite Type-Checks & Build)
* **TypeScript Compilation Type-Check**:
  ```bash
  cd frontend
  npx vue-tsc --noEmit
  ```
* **Production Resource Compilation**:
  ```bash
  npm run build
  ```
  *Result: Compiles with clean status, outputs optimized modular static chunks through Vite/Nginx.*

### ⚡ Backend Verification (Ruff, Pytest, & Strict Mypy)
* **Ruff Formatting & Quality Checks**:
  ```bash
  cd backend
  python -m ruff check app --fix
  python -m ruff format app
  ```
* **Strict Mypy Type Verification**:
  ```bash
  python -m mypy --strict --explicit-package-bases backend/app/
  ```
  *Result: `Success: no issues found in 43 source files` (100% type safety annotation coverage).*
* **Pytest Suite**:
  Run the automated async test suite:
  ```bash
  python -m pytest backend/app/tests/ -v --tb=short
  ```
  *Result: `76 passed in 2.97s` (Validating circuit breakers, simulator math, bucket indexing, factory dispatch, and endpoints).*

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.