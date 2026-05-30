<div align="center">

# 📊 Cryptex — Real-Time Market Intelligence Center

[![Build & E2E Validation](https://img.shields.io/badge/Build--Validation-Passing-059669?style=for-the-badge&logo=github-actions&logoColor=white)](https://github.com)
[![Vue 3 Composition API](https://img.shields.io/badge/Vue--3--Composition--TS-Strict--No--Emit-41B883?style=for-the-badge&logo=vue.js&logoColor=white)](https://vuejs.org)
[![FastAPI Async](https://img.shields.io/badge/FastAPI-Fully--Async--0.136+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Google Gemma LLM](https://img.shields.io/badge/AI--Engine-Google--Gemma--31B-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://openrouter.ai/)
[![Docker Multi-Network](https://img.shields.io/badge/Docker-Hardened--Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com)

**An Enterprise-grade, high-frequency cryptocurrency and equity sentiment intelligence dashboard.**  
Engineered with async-safe design patterns, FSM circuit breakers, log-normal market simulators, and production-hardened network topologies.

[Live Application Demo](http://localhost:8080) · [Backend API Sandbox](http://localhost:8000/docs) · [Report Bug](https://github.com/your-username/crypto-sentiment-analyzer/issues)

<br>

<img src="./frontend_dashboard.png" alt="Cryptex Dashboard Preview" width="900" style="border-radius: 12px; box-shadow: 0px 10px 30px rgba(0,0,0,0.5);">

</div>

---

## ✨ Enterprise Features

| Feature | Description | Stack |
|---------|-------------|-------|
| **🚀 Factory-Driven Scalability** | Fully abstracts data fetching. Adding new crypto/stocks requires changing **one line of config**. | *SOLID, Abstract Base Classes* |
| **🛡️ 3-State FSM Circuit Breaker** | Instantly catches downstream LLM/API timeouts and redirects to local fallback without freezing the Event Loop. | *FastAPI, Asyncio* |
| **🧠 Real-Time AI Sentiment** | Ingests live Google News RSS feeds and analyzes them asynchronously via Google Gemma (via OpenRouter). | *OpenRouter, httpx* |
| **🧮 GBM Market Simulator** | Generates log-normal Geometric Brownian Motion simulated prices when external APIs hit Rate Limits (429). | *NumPy, Async Threading* |
| **🎨 Premium Fluid UI** | Beautiful Glassmorphism, CSS `@container` queries, 60Hz WebSocket reactive rendering, and high-fidelity `<TransitionGroup>` animation system for live news. | *Vue 3, Tailwind, ECharts* |
| **🔐 Hardened Docker Topologies** | Private internal-only networks for MongoDB. Strict auth enforced, matching Atlas cloud parity. | *Docker Compose* |

---

## 🏗️ System Architecture Blueprint

```mermaid
graph TD
    subgraph Frontend["Vue 3 SPA (Client)"]
        V["Vue 3 Components Setup TS"] <--> PQ["TanStack Vue Query Caches"]
        V <--> P["Pinia Client States"]
        V <--> WS_C["useWebSocketManager"]
    end

    subgraph Backend["FastAPI Engine (Python 3.12 Fully Async)"]
        E["API Endpoints & Routers"] <--> WS_S["websocket_endpoint (Slow Client Shield)"]
        BUL["background_update_loop"]
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

    subgraph AI["AI Pipeline / Fallback"]
        LLM_API["Google Gemma via OpenRouter"]
        Vader["Local VADER Sentiment Engine"]
    end

    subgraph Database["Persistence Layer (Isolated Network)"]
        DB[("MongoDB Container (Auth Enforced)")]
    end

    PQ <--> E
    WS_C <--> WS_S
    BUL --> F
    CH -- "Success Paths" --> DB
    BUL -- "Exception caught" --> SIM
    SIM -- "GBM fallback stream" --> DB
    Parser --> CB
    CB -- "CLOSED (Success)" --> LLM_API
    CB -- "OPEN (Fallback)" --> Vader
    Parser --> DB
    E --> DB
```

---

## ⚙️ Development Environment Setup

Launch the complete multi-container enterprise stack locally in minutes:

### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed and running.
- An [OpenRouter API Key](https://openrouter.ai/) (Free Tier supported with built-in Concurrency Limiters).

### 2. Configure Environment
Clone the repository and set up your environment variables:
```bash
git clone https://github.com/your-username/crypto-sentiment-analyzer.git
cd crypto-sentiment-analyzer
cp backend/.env.example backend/.env
```

Edit `backend/.env` with your secure credentials:
```env
# Local Hardened MongoDB Connection (Auth enforced)
MONGODB_URL=mongodb://root:admin_secure_password@mongodb:27017
MONGODB_DB_NAME=sentiment_db

# OpenRouter AI Sentiment Pipeline
LLM_API_URL=https://openrouter.ai/api/v1
LLM_MODEL=google/gemma-4-31b-it:free
LLM_API_KEY=your_openrouter_key

# secure hex key (generate with python -c "import secrets; print(secrets.token_hex(32))")
JWT_SECRET_KEY=your_secure_jwt_key
```

### 3. Orchestrate Container Startup
Launch the hardened container stack using Docker Compose:
```bash
docker compose up --build -d
```
> [!NOTE]
> The backend automatically paces AI inference requests to respect OpenRouter Free Tier rate limits (429). Initial historical data seeding may take 1-2 minutes.

### 4. Access the Platform
- 📊 **Live Dashboard**: [http://localhost:8080](http://localhost:8080)
- 🧠 **API Swagger Sandbox**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🛠️ Code Quality & Verification Gates

Quality checks are strictly enforced across both front-end and back-end stacks. All gates must pass with **zero warnings/errors** before deployment.

### 🧪 E2E UI Testing
```bash
python scripts/check_buttons.py
```
*Validates that LLM data correctly flows through WebSockets into the DOM and successfully renders AI Analysis Badges.*

### ⚡ Backend Verification (Ruff, Pytest, & Strict Mypy)
The backend is strictly typed and adheres to standard formatting requirements:
```bash
cd backend
python -m ruff check app --fix
python -m mypy --strict --explicit-package-bases backend/app/
python -m pytest backend/app/tests/ -v --tb=short
```

### 🎨 Frontend Compilation & Type Safety
The frontend has 100% strict type safety (no `any` occurrences) and validates perfectly:
```bash
cd frontend
npx vue-tsc --noEmit && npm run build
```

---

<div align="center">
  <sub>Built with ❤️ by an expert Full-Stack Architect. Distributed under the MIT License.</sub>
</div>