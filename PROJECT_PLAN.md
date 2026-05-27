# LLM-Powered Market Sentiment Analyzer

## 🎯 Project Objective
Build a sophisticated, real-time analytics dashboard that aggregates market data (crypto/stocks), processes news/social media feeds through a Local LLM for sentiment analysis (Bullish/Bearish), and visualizes the results. 

This project serves as a technical showcase of advanced Vue.js frontend architecture, modern API integration, and asynchronous data processing.

## 🏗 System Architecture

### 1. Frontend (Vue 3 SPA)
The user interface is a responsive, dark-themed dashboard.
* **Metrics Panel:** Displays real-time price data and 24h changes.
* **Sentiment Chart:** An interactive ECharts visualization showing price action overlaid with LLM-generated sentiment scores over time.
* **Live Feed:** A virtualized list of recent news/tweets, color-coded by sentiment.
* **State Management:** Vue Query handles all async data fetching, caching, and background updates. Pinia manages user preferences (e.g., selected asset, timeframe).

### 2. Backend (FastAPI)
A lightweight, high-performance API layer.
* **Endpoints:**
  - `GET /api/v1/assets/{asset_id}/metrics` (Price data)
  - `GET /api/v1/assets/{asset_id}/sentiment` (LLM analysis results)
* **Data Processing:** Asynchronous web scraping engine that feeds text data to an LLM (mocked via simple logic for the MVP, later connected to LM Studio/Ollama).

## 🚀 Implementation Phases

### Phase 1: Frontend MVP & UI Scaffolding (Mock Data)
1. Initialize Vite + Vue 3 + TS project.
2. Setup Tailwind CSS and shadcn-vue base components.
3. Build the static Dashboard layout (Sidebar, Header, Main Grid).
4. Create complex Mock JSON data (prices, timestamps, sentiment scores).
5. Implement `vue-echarts` to render the Mock data beautifully.

### Phase 2: Reactivity & State Management
1. Integrate `@tanstack/vue-query` to fetch the Mock data.
2. Add interactive filters (e.g., "1H", "24H", "7D" timeframes) that trigger reactive UI updates.
3. Implement loading skeletons and error boundary states.

### Phase 3: Backend API Integration
1. Scaffold the FastAPI backend.
2. Replace frontend Mock data calls with real HTTP requests to the FastAPI endpoints.
3. Ensure CORS is configured and the data pipeline flows smoothly.

### Phase 4: Polish & Containerization
1. Write a `docker-compose.yml` to spin up both the Frontend (via Nginx or Vite preview) and Backend together.
2. Optimize Lighthouse score (performance, accessibility).