# Cryptex — Phased Improvement Plan

> **Scope:** Frontend UI/UX, backend optimization, hardcode elimination, modularity, and adaptive design.  
> **Convention:** Each item follows the pattern *Current State → Target State → Implementation → File: `path` (section or approximate lines)*.

---

## Phase 1 — Critical Bug Fixes (Breaking Issues)
**Estimated effort: 1–2 days**  
These are runtime bugs that either produce a `NameError`/`ImportError` or silently break a feature. Fix these before any refactoring.

---

### 1.1 — Wrong `settings` import inside `ai_chat` route handler

**Current state**
```python
# inside the ai_chat handler body
from backend.app.handlers.config import settings
```
`backend/app/handlers/config.py` only exports `HANDLER_CONFIG`. Importing `settings` from it raises `ImportError: cannot import name 'settings'` at the first call to `/api/v1/chat`.

**Target state**
```python
from backend.app.core.config import settings
```

**File:** `backend/app/api/v1/endpoints.py` — inside the `ai_chat` function body (two imports after `from backend.app.services.llm import get_llm_client`).

---

### 1.2 — `Optional` not imported in `endpoints.py`

**Current state**
```python
from typing import Any, Dict, List
# ...
last_error: Optional[Exception] = None   # NameError at runtime
```

**Target state**
```python
from typing import Any, Dict, List, Optional
```

**File:** `backend/app/api/v1/endpoints.py` — top-level imports block (line ~13).

---

### 1.3 — `_calculate_vader_score` called but never defined

**Current state**
```python
def analyze_sentiment_local(title: str, summary: str) -> Dict[str, Any]:
    title_score = _calculate_vader_score(title)    # NameError
    summary_score = _calculate_vader_score(summary) # NameError
```
The helper is referenced throughout `analyze_sentiment_local` but the function body is absent from the file (likely truncated). Without it the entire local VADER engine raises `NameError` on first use.

**Target state** — add the missing function above `analyze_sentiment_local`:
```python
def _calculate_vader_score(text: str) -> float:
    """
    Scores a single text string using the CRYPTO_LEXICON with negation,
    intensifier, contrastive-but, and capitalisation adjustments.
    """
    tokens = _tokenize_text(text)
    score: float = 0.0
    for i, token in enumerate(tokens):
        clean = _clean_token(token)
        if not clean:
            continue
        valence = CRYPTO_LEXICON.get(clean, 0.0)
        if valence == 0.0:
            continue
        # Capitalisation boost
        if _is_all_caps(token) and abs(valence) > 0:
            valence += 0.733 if valence > 0 else -0.733
        # Negation (look back up to 3 tokens)
        preceding = [_clean_token(tokens[j]) for j in range(max(0, i - 3), i)]
        if any(neg in NEGATIONS for neg in preceding):
            valence *= -0.74
        # Intensifiers (immediately preceding token)
        if i > 0:
            prev = _clean_token(tokens[i - 1])
            valence += valence * INCREMENTAL_INTENSIFIERS.get(prev, 0.0)
            valence += valence * DECREMENTAL_INTENSIFIERS.get(prev, 0.0)
        score += valence

    # Contrastive "but" — weight post-but clause 1.5×, pre-but 0.5×
    lower = text.lower()
    if " but " in lower:
        parts = lower.split(" but ", 1)
        pre_score = _calculate_vader_score(parts[0])
        post_score = _calculate_vader_score(parts[1])
        score = pre_score * 0.5 + post_score * 1.5

    return score
```

**File:** `backend/app/services/sentiment_engine.py` — immediately before `analyze_sentiment_local` (end of file).

---

### 1.4 — `anyio` missing from test requirements

**Current state**  
`pytest.ini` has no async mode configured, and `requirements.txt` omits `anyio` and its pytest plugin. Tests decorated with `@pytest.mark.anyio` silently skip or raise a collection error depending on the installed `pytest` version.

**Target state**
```
# requirements.txt — add at bottom of test tooling block
anyio[trio]==4.4.0
pytest-anyio==0.0.0  # ships with anyio 4.x; pin anyio is sufficient
```
```ini
# pytest.ini
[pytest]
filterwarnings =
    ignore::DeprecationWarning
asyncio_mode = auto
```

**File:** `backend/requirements.txt` (append), `pytest.ini` (add `asyncio_mode`).

---

## Phase 2 — Configuration Centralization
**Estimated effort: 2–3 days**  
All magic numbers, feature-flag strings, and operational thresholds are scattered across seven different modules. Centralizing them in `Settings` makes the app configurable via environment variables without code changes.

---

### 2.1 — Extend the `Settings` class with all currently hardcoded constants

**Current state** — the following values are hardcoded across multiple modules:

| Constant | Hardcoded location |
|---|---|
| `_BACKOFF_START_SECONDS = 5.0` | `backend/app/main.py` line ~28 |
| `_BACKOFF_MAX_SECONDS = 300.0` | `backend/app/main.py` line ~29 |
| `_HEALTHY_RUN_SECONDS = 60.0` | `backend/app/main.py` line ~30 |
| CORS origins list | `backend/app/main.py` lines ~192–205 |
| `_MAX_BACKGROUND_RPM: int = 8` | `backend/app/services/llm.py` line ~155 |
| `failure_threshold=3, recovery_timeout=60.0` | `backend/app/services/llm.py` line ~175 |
| `MAX_ARTICLES_PER_SWEEP: int = 15` | `backend/app/services/parser.py` line ~35 |
| `MAX_AAPL_ARTICLES_PER_SWEEP: int = 3` | `backend/app/services/parser.py` line ~36 |
| LLM fallback model chain (3 strings) | `backend/app/services/llm.py` lines ~285–292 and duplicated in `endpoints.py` lines ~130–135 |

**Target state** — extend `backend/app/core/config.py`:
```python
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── Database ──────────────────────────────────────────────────────────
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "sentiment_db"

    # ── LLM / OpenRouter ──────────────────────────────────────────────────
    LLM_API_URL: Optional[str] = None
    LLM_MODEL: str = "google/gemini-2.0-flash-exp"
    LLM_API_KEY: Optional[str] = None
    # Comma-separated fallback chain tried in order after primary model fails.
    LLM_FALLBACK_MODELS: str = (
        "google/gemini-2.5-flash:free,"
        "meta-llama/llama-3-8b-instruct:free,"
        "mistralai/mistral-7b-instruct:free"
    )
    # Max background LLM requests per 60-second window (preserves free-tier budget)
    LLM_MAX_BACKGROUND_RPM: int = 8

    # ── Circuit Breaker ───────────────────────────────────────────────────
    CB_FAILURE_THRESHOLD: int = 3
    CB_RECOVERY_TIMEOUT: float = 60.0

    # ── RSS Parser ────────────────────────────────────────────────────────
    RSS_MAX_ARTICLES_PER_SWEEP: int = 15
    RSS_MAX_AAPL_ARTICLES: int = 3

    # ── Task Supervisor (exponential backoff) ──────────────────────────────
    TASK_BACKOFF_START: float = 5.0
    TASK_BACKOFF_MAX: float = 300.0
    TASK_HEALTHY_RUN_SECONDS: float = 60.0

    # ── CORS (comma-separated allowed origins) ────────────────────────────
    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://localhost:4173,"
        "http://127.0.0.1:5173,"
        "http://127.0.0.1:4173,"
        "http://localhost:8080,"
        "http://127.0.0.1:8080,"
        "https://crypto-market-sentiment-analyzer-1.onrender.com"
    )

    # ── Auth ──────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_ENV_VAR"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── External APIs ─────────────────────────────────────────────────────
    ALCHEMY_API_KEY: Optional[str] = None

    # ── Computed properties ───────────────────────────────────────────────
    @property
    def llm_fallback_models_list(self) -> list[str]:
        """Returns the parsed, deduplicated fallback model chain."""
        seen: set[str] = set()
        result: list[str] = []
        for model in [self.LLM_MODEL] + [
            m.strip() for m in self.LLM_FALLBACK_MODELS.split(",") if m.strip()
        ]:
            if model not in seen:
                seen.add(model)
                result.append(model)
        return result

    @property
    def cors_origins_list(self) -> list[str]:
        """Returns the parsed list of allowed CORS origins."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
```

**File:** `backend/app/core/config.py` — replace entire file content.

---

### 2.2 — Consume `settings` in `main.py` (backoff + CORS)

**Current state**
```python
_BACKOFF_START_SECONDS = 5.0
_BACKOFF_MAX_SECONDS = 300.0
_HEALTHY_RUN_SECONDS = 60.0
# ...
origins = [
    "http://localhost:5173",
    # ... 7 hardcoded strings
]
app.add_middleware(CORSMiddleware, allow_origins=origins, ...)
```

**Target state**
```python
from backend.app.core.config import settings

_BACKOFF_START_SECONDS = settings.TASK_BACKOFF_START
_BACKOFF_MAX_SECONDS   = settings.TASK_BACKOFF_MAX
_HEALTHY_RUN_SECONDS   = settings.TASK_HEALTHY_RUN_SECONDS
# ...
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://.*\.onrender\.com|https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**File:** `backend/app/main.py` — module-level constants (lines ~27–30) and `origins` list + middleware call (lines ~190–215).

---

### 2.3 — Consume `settings` in `llm.py` (RPM cap + circuit breaker + fallback chain)

**Current state**
```python
_MAX_BACKGROUND_RPM: int = 8
# ...
_sentiment_breaker = CircuitBreaker(
    name="sentiment_engine",
    failure_threshold=3,
    recovery_timeout=60.0,
)
# ...
model_chain = [
    settings.LLM_MODEL,
    "google/gemini-2.5-flash:free",
    "meta-llama/llama-3-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free"
]
```

**Target state**
```python
from backend.app.core.config import settings

_MAX_BACKGROUND_RPM: int = settings.LLM_MAX_BACKGROUND_RPM
# ...
_sentiment_breaker = CircuitBreaker(
    name="sentiment_engine",
    failure_threshold=settings.CB_FAILURE_THRESHOLD,
    recovery_timeout=settings.CB_RECOVERY_TIMEOUT,
)
# ...
# In _call_openrouter:
model_chain = settings.llm_fallback_models_list
```

**File:** `backend/app/services/llm.py` — module-level constants (lines ~155, ~175) and inside `_call_openrouter` and `analyze_articles_batch` (lines ~285–292, ~380–385).

---

### 2.4 — Consume `settings` in `parser.py` (sweep limits)

**Current state**
```python
MAX_ARTICLES_PER_SWEEP: int = 15
MAX_AAPL_ARTICLES_PER_SWEEP: int = 3
MAX_LLM_CALLS_PER_SWEEP: int = 3
```

**Target state**
```python
from backend.app.core.config import settings

MAX_ARTICLES_PER_SWEEP     = settings.RSS_MAX_ARTICLES_PER_SWEEP
MAX_AAPL_ARTICLES_PER_SWEEP = settings.RSS_MAX_AAPL_ARTICLES
```

`MAX_LLM_CALLS_PER_SWEEP` is unused in the current implementation — **delete it entirely**.

**File:** `backend/app/services/parser.py` — module-level constants block (lines ~35–38).

---

### 2.5 — Eliminate the duplicate model fallback chain in `endpoints.py`

**Current state**  
The `ai_chat` handler manually rebuilds the same fallback chain that `llm.py` owns:
```python
model_chain = [
    settings.LLM_MODEL,
    "google/gemini-2.5-flash:free",
    "meta-llama/llama-3-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free"
]
models = []
for m in model_chain:
    if m not in models:
        models.append(m)
```

**Target state**
```python
models = settings.llm_fallback_models_list
```

**File:** `backend/app/api/v1/endpoints.py` — inside `ai_chat` function body (lines ~130–140).

---

## Phase 3 — Backend Architecture & Modularity
**Estimated effort: 3–4 days**  
These changes remove structural duplication and fix shared mutable state that is unsafe in async contexts.

---

### 3.1 — Derive `ASSET_REGEX` from `HANDLER_CONFIG` (single source of truth)

**Current state**  
`ASSET_REGEX` in `parser.py` is a manually maintained dictionary with 16 entries. Adding an asset to `HANDLER_CONFIG` does not update the parser — a developer must edit two files.

```python
ASSET_REGEX: Dict[str, re.Pattern[str]] = {
    "BTC": re.compile(r"\b(bitcoin|btc)\b", re.IGNORECASE),
    "ETH": re.compile(r"\b(ethereum|eth|ether)\b", re.IGNORECASE),
    # ... 14 more hardcoded entries
}
```

**Target state**  
Add an `aliases` field to every entry in `HANDLER_CONFIG`, then derive `ASSET_REGEX` automatically:

```python
# In backend/app/handlers/config.py — each asset entry gains:
{
    "type": "crypto",
    "id": "BTC",
    "name": "Bitcoin",
    "aliases": ["bitcoin", "btc"],          # ← NEW
    "coingecko_id": "bitcoin",
    ...
}
# ETH example:
{
    "aliases": ["ethereum", "eth", "ether"],
}
# AAPL example:
{
    "aliases": ["apple", "aapl", "apple inc"],
}
```

```python
# In backend/app/services/parser.py — replace the hardcoded dict:
import re
from backend.app.handlers.config import HANDLER_CONFIG

def _build_asset_regex() -> dict[str, re.Pattern[str]]:
    """Derives per-asset keyword patterns from HANDLER_CONFIG.aliases."""
    regex: dict[str, re.Pattern[str]] = {}
    for cfg in HANDLER_CONFIG:
        asset_id = str(cfg["id"])
        raw_aliases: list[str] = list(cfg.get("aliases", [asset_id.lower()]))
        pattern = r"\b(" + "|".join(re.escape(a) for a in raw_aliases) + r")\b"
        regex[asset_id] = re.compile(pattern, re.IGNORECASE)
    return regex

ASSET_REGEX: dict[str, re.Pattern[str]] = _build_asset_regex()
```

Adding any new asset to `HANDLER_CONFIG` with an `aliases` key now automatically registers it in the parser. **Zero other files change.**

**Files:**  
- `backend/app/handlers/config.py` — add `"aliases": [...]` to every dict entry  
- `backend/app/services/parser.py` — replace `ASSET_REGEX` constant block (lines ~40–60) with the builder function

---

### 3.2 — Consolidate the two TTLCache implementations

**Current state**  
The codebase uses two different TTLCache implementations simultaneously:

- `backend/app/core/cache.py` — custom lazy-eviction `TTLCache` (the canonical singleton `cache`)
- `backend/app/api/v1/endpoints.py` — imports `cachetools.TTLCache` (a third-party implementation) for `_fng_cache`, `_assets_cache`, `_metrics_cache`, `_sentiment_cache`

This creates inconsistency: one uses monotonic time, the other uses wall-clock time; one supports `key, value, ttl` call signature, the other uses `maxsize` + `ttl` at construction.

**Target state**  
Remove `cachetools` from the endpoints file and replace all four `TTLCache` usages with the project's own `cache` singleton, using namespaced keys:

```python
# Before (in endpoints.py):
from cachetools import TTLCache
_fng_cache = TTLCache(maxsize=1, ttl=3600)
_assets_cache = TTLCache(maxsize=1, ttl=15)
_metrics_cache = TTLCache(maxsize=50, ttl=15)
_sentiment_cache = TTLCache(maxsize=50, ttl=30)

# After:
from backend.app.core.cache import cache   # already exists

# Usage in get_fear_greed:
cached = cache.get("fng:latest")
if cached is not None:
    return cached
# ...
cache.set("fng:latest", result, ttl_seconds=3600)

# Usage in list_assets:
cached = cache.get("assets:all")
if cached is not None:
    return cached
# ...
cache.set("assets:all", result, ttl_seconds=15)

# Usage in get_asset_metrics (per-asset key):
cached = cache.get(f"metrics:{asset_id}")
# ...
cache.set(f"metrics:{asset_id}", result, ttl_seconds=15)

# Usage in get_asset_sentiment:
cached = cache.get(f"sentiment:{asset_id}")
# ...
cache.set(f"sentiment:{asset_id}", result, ttl_seconds=30)
```

Remove `cachetools` from `requirements.txt` after verifying no other module uses it.

**Files:**  
- `backend/app/api/v1/endpoints.py` — imports block (remove `from cachetools import TTLCache`, lines ~30–35) and all four cache declaration lines  
- `backend/requirements.txt` — remove `cachetools>=5.5.0`

---

### 3.3 — Fix global mutable state in `llm.py`

**Current state**  
Two module-level mutable objects create race-condition risk in async contexts:
```python
_bg_call_timestamps: List[float] = []      # mutable list shared across all coroutines
_llm_client: Optional[httpx.AsyncClient] = None  # mutable global reference
```

**Target state**  
Replace the sliding-window list with a proper async-safe counter class, and expose the client via a function that checks for closure:

```python
import asyncio
import time
from dataclasses import dataclass, field

@dataclass
class _SlidingWindowCounter:
    """Async-safe token-bucket for the background LLM rate limiter."""
    max_calls: int
    window_seconds: float
    _timestamps: list[float] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def is_allowed(self) -> bool:
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds
            self._timestamps = [t for t in self._timestamps if t >= cutoff]
            if len(self._timestamps) >= self.max_calls:
                return False
            self._timestamps.append(now)
            return True

_bg_rate_limiter = _SlidingWindowCounter(
    max_calls=settings.LLM_MAX_BACKGROUND_RPM,
    window_seconds=60.0,
)

# Replace _background_rate_limit_ok with:
async def _background_rate_limit_ok() -> bool:
    return await _bg_rate_limiter.is_allowed()
```

For the shared client, use the project's existing `get_shared_client()` from `backend.app.core.http_client` rather than maintaining a second singleton:
```python
# Remove:
_llm_client: Optional[httpx.AsyncClient] = None

def get_llm_client() -> httpx.AsyncClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = httpx.AsyncClient(timeout=15.0)
    return _llm_client

# Replace usages with:
from backend.app.core.http_client import get_shared_client
# (get_shared_client already handles pooling and lifecycle)
```

**File:** `backend/app/services/llm.py` — `_bg_call_timestamps` declaration and `_background_rate_limit_ok` function, plus `_llm_client` declaration and `get_llm_client` function.

---

### 3.4 — Move all lazy imports to module level

**Current state**  
Across `endpoints.py`, `market_data.py`, and `parser.py`, many imports are deferred inside function bodies. This hides dependency relationships and defeats type-checkers.

```python
# Examples found in endpoints.py (ai_chat, analyze_article_sentiment_endpoint, etc.):
async def ai_chat(...):
    from backend.app.services.llm import get_llm_client
    from backend.app.handlers.config import settings      # also wrong, see 1.1
    ...

async def analyze_article_sentiment_endpoint(...):
    import httpx
    from backend.app.services.llm import (llm_cache, analyze_article_sentiment, clean_text)
    from backend.app.services.parser import _apply_sentiment_to_asset
    ...

# Examples in market_data.py (background_update_loop):
async def background_update_loop():
    from backend.app.services.price_feed import fetch_onchain_metrics
    from backend.app.services.aggregator import aggregator
    from backend.app.services.simulator import simulate_price_tick
    from backend.app.schemas.market import AssetMetrics
    ...
```

**Target state**  
Move all imports to the top of each file. Where circular imports would result, use dependency injection via function parameters or restructure the module boundary.

```python
# backend/app/api/v1/endpoints.py — top-level additions:
import httpx
from backend.app.core.config import settings
from backend.app.services.llm import (
    llm_cache,
    analyze_article_sentiment,
    clean_text,
    get_llm_client,
)
from backend.app.services.parser import _apply_sentiment_to_asset

# backend/app/services/market_data.py — top-level additions:
from backend.app.services.price_feed import fetch_onchain_metrics
from backend.app.services.aggregator import aggregator
from backend.app.services.simulator import simulate_price_tick
from backend.app.schemas.market import AssetMetrics
```

Verify import ordering with `ruff check --select I` after moving.

**Files:**  
- `backend/app/api/v1/endpoints.py` — imports block (lines ~1–50)  
- `backend/app/services/market_data.py` — imports block (lines ~1–30)

---

### 3.5 — Add return type annotation to `HttpClient.close`

**Current state**
```python
@classmethod
async def close(cls):          # missing return type
    if cls._client and not cls._client.is_closed:
        await cls._client.aclose()
        cls._client = None
```

**Target state**
```python
@classmethod
async def close(cls) -> None:
    ...
```

**File:** `backend/app/core/http_client.py` — `HttpClient.close` method.

---

## Phase 4 — Frontend Hardcode Elimination & Adaptive Registry
**Estimated effort: 2–3 days**  
The frontend maintains seven separate hardcoded lists of asset IDs that must all be updated manually when the backend adds a new asset. This phase replaces them with API-driven or fallback-safe patterns.

---

### 4.1 — Centralize the API base URL (single declaration point)

**Current state**  
The fallback `'http://localhost:8000'` appears in two independent files:
```typescript
// frontend/src/services/api.ts line ~25
const BASE_URL = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/api/v1`

// frontend/src/composables/useWebSocketManager.ts line ~100
const rawApiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
```

**Target state**  
Create `frontend/src/constants/env.ts`:
```typescript
/**
 * Single source of truth for all environment-derived constants.
 * Import from here — never access import.meta.env directly in components.
 */
export const API_HTTP_BASE = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/api/v1`
export const API_WS_BASE   = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/^http/, 'ws')
export const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 15_000)
```

Then consume in both files:
```typescript
// api.ts
import { API_HTTP_BASE } from '@/constants/env'
const BASE_URL = API_HTTP_BASE

// useWebSocketManager.ts
import { API_WS_BASE } from '@/constants/env'
const wsUrl = `${API_WS_BASE}/api/v1/ws/${id}`
```

**Files:**  
- Create `frontend/src/constants/env.ts`  
- `frontend/src/services/api.ts` — line ~25  
- `frontend/src/composables/useWebSocketManager.ts` — line ~100

---

### 4.2 — Make `VALID_ASSET_IDS` in the router resilient to unknown assets

**Current state**  
```typescript
// frontend/src/router/index.ts lines ~12–17
const VALID_ASSET_IDS = new Set<RouteAssetId>([
  'BTC', 'ETH', 'SOL', 'AAPL', 'TON', 'XRP', 'ADA',
  'DOGE', 'DOT', 'LINK', 'AVAX', 'MATIC', 'SHIB', 'LTC', 'UNI', 'NEAR', 'ATOM',
])
```
When the backend registers a new asset, the router rejects navigation to `/asset/NEWASSET` with a silent redirect to BTC — confusing for users.

**Target state**  
Keep the static set as a "known-good" fast path, but **allow unknown IDs through** and let the API's 404 response on `/assets/{id}/metrics` be the authoritative gatekeeper. Replace the hard redirect with a pass-through:

```typescript
// frontend/src/router/index.ts
const KNOWN_ASSET_IDS = new Set<RouteAssetId>([
  'BTC', 'ETH', 'SOL', 'AAPL', 'TON', 'XRP', 'ADA',
  'DOGE', 'DOT', 'LINK', 'AVAX', 'MATIC', 'SHIB', 'LTC', 'UNI', 'NEAR', 'ATOM',
])

router.beforeEach((to) => {
  if (to.name === 'dashboard') {
    const id = to.params.id as string
    // Only hard-redirect if the ID is clearly invalid (empty or non-uppercase)
    if (!id || !/^[A-Z0-9]{1,10}$/.test(id)) {
      return { name: 'dashboard', params: { id: DEFAULT_ASSET }, replace: true }
    }
    // Known IDs pass instantly; unknown IDs pass through and hit the API 404 UX
  }
  // ... auth guards unchanged
})

// Export both for use in type-safe components:
export { DEFAULT_ASSET, KNOWN_ASSET_IDS }
```

Also update `RouteAssetId` in `frontend/src/types/market.ts` to include a catch-all:
```typescript
export type RouteAssetId =
  | 'BTC' | 'ETH' | 'SOL' | 'AAPL' | 'TON' | 'XRP' | 'ADA'
  | 'DOGE' | 'DOT' | 'LINK' | 'AVAX' | 'MATIC' | 'SHIB' | 'LTC'
  | 'UNI' | 'NEAR' | 'ATOM'
  | (string & {})  // allows unknown assets to pass type-checking as strings
```

**Files:**  
- `frontend/src/router/index.ts` — `VALID_ASSET_IDS` block (lines ~12–17) and the guard (lines ~45–55)  
- `frontend/src/types/market.ts` — `RouteAssetId` type (line ~2)

---

### 4.3 — Add fallback color generation in `useCryptoFormatters`

**Current state**  
```typescript
export function getAssetBrandColor(symbol: RouteAssetId): string {
  return ASSET_BRAND_COLORS[symbol]   // returns undefined for unknown assets
}
```
Any unknown asset causes downstream `undefined` where a color string is expected (broken inline styles, invisible SVG elements).

**Target state**  
```typescript
/** Deterministic hex color derived from the asset ticker string. */
function _deriveColorFromSymbol(symbol: string): string {
  let hash = 0
  for (let i = 0; i < symbol.length; i++) {
    hash = symbol.charCodeAt(i) + ((hash << 5) - hash)
  }
  const hue = Math.abs(hash) % 360
  return `hsl(${hue}, 65%, 55%)`
}

export function getAssetBrandColor(symbol: string): string {
  return (ASSET_BRAND_COLORS as Record<string, string>)[symbol]
    ?? _deriveColorFromSymbol(symbol)
}

export function getAssetGradient(symbol: string): string {
  const color = getAssetBrandColor(symbol)
  return (ASSET_GRADIENTS as Record<string, string>)[symbol]
    ?? `linear-gradient(135deg, ${color}18 0%, ${color}03 100%)`
}
```

Change all call-sites that accept `RouteAssetId` to accept `string` for these two functions — no other behavior changes.

**File:** `frontend/src/composables/useCryptoFormatters.ts` — `getAssetBrandColor` and `getAssetGradient` functions (lines ~67–80, ~85–95).

---

### 4.4 — Consolidate the four hardcoded asset order lists

**Current state**  
Four separate arrays define asset display order, all maintained independently:

| Array | File | Approximate line |
|---|---|---|
| `GRID_ORDER` | `MarketOverviewGrid.vue` | ~50 |
| `CRYPTO_IDS` | `Sidebar.vue` | ~70 |
| `GRID_ASSETS` | `SentimentHeatmap.vue` | ~65 |
| `CRYPTO_IDS` (again) | `CryptoTickerBar.vue` | ~30 |

**Target state**  
Create `frontend/src/constants/assets.ts`:
```typescript
import type { RouteAssetId } from '@/types/market'

/** Canonical display order for crypto assets across all dashboard components. */
export const CRYPTO_ASSET_ORDER: RouteAssetId[] = [
  'BTC', 'ETH', 'SOL', 'TON', 'XRP', 'ADA',
  'DOGE', 'DOT', 'LINK', 'AVAX', 'MATIC', 'SHIB', 'LTC', 'UNI', 'NEAR', 'ATOM',
]

/** Assets displayed in the sentiment heatmap (subset of the above). */
export const HEATMAP_ASSET_IDS: RouteAssetId[] = [
  'BTC', 'ETH', 'TON', 'SOL', 'XRP', 'ADA',
]

/** The asset the router redirects to when no valid ID is present. */
export const DEFAULT_ASSET: RouteAssetId = 'BTC'
```

Then import `CRYPTO_ASSET_ORDER` in all four components, removing local declarations.

**Files:**  
- Create `frontend/src/constants/assets.ts`  
- `frontend/src/components/dashboard/MarketOverviewGrid.vue` — remove `GRID_ORDER`, import from constants  
- `frontend/src/components/layout/Sidebar.vue` — remove `CRYPTO_IDS`, import from constants  
- `frontend/src/components/dashboard/SentimentHeatmap.vue` — remove `GRID_ASSETS`, import `HEATMAP_ASSET_IDS`  
- `frontend/src/components/dashboard/CryptoTickerBar.vue` — remove `CRYPTO_IDS` equivalent, import from constants  
- `frontend/src/router/index.ts` — import `DEFAULT_ASSET` from constants (remove local const)

---

### 4.5 — Fix `vite-env.d.ts` type safety

**Current state**
```typescript
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>   // `any` violates strict mode
  export default component
}
```

**Target state**
```typescript
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_API_TIMEOUT_MS?: string
  readonly VITE_LLM_MODEL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<
    Record<string, unknown>,
    Record<string, unknown>,
    unknown
  >
  export default component
}
```

This makes all `import.meta.env.VITE_*` accesses type-safe throughout the frontend.

**File:** `frontend/src/vite-env.d.ts` — full file replacement.

---

## Phase 5 — Frontend UI/UX Polish
**Estimated effort: 1–2 days**  
Cosmetic and interaction fixes that improve usability without altering architecture.

---

### 5.1 — Account for `TerminalStatusBar` in the main scroll area

**Current state**  
`TerminalStatusBar` is `position: fixed; bottom: 0; height: 24px (h-6)` and sits on top of content. The main scrollable area has no bottom padding, so the last few pixels of any long page are permanently obscured behind the bar.

**Target state**  
Add a global bottom padding to the main scroll container. In `App.vue`, the authenticated shell renders:
```html
<!-- Current: -->
<RouterView />

<!-- Target: add padding-bottom to account for h-6 (24px) status bar -->
<div class="flex-1 overflow-y-auto pb-6">
  <RouterView />
</div>
```

Additionally, the status bar should not overlap the AI chat FAB. Adjust the chat widget's `bottom-6` positioning to `bottom-10` so the button sits above the bar:

```html
<!-- AIChatWidget.vue: change fixed positioning class -->
<!-- Before: -->
<div class="fixed bottom-6 right-6 z-50 ...">

<!-- After: -->
<div class="fixed bottom-10 right-6 z-50 ...">
```

**Files:**  
- `frontend/src/App.vue` — the `<RouterView />` wrapper inside the authenticated shell (line ~57)  
- `frontend/src/components/AIChatWidget.vue` — outer `div` fixed positioning class (line ~63)

---

### 5.2 — Handle private-browsing `localStorage` failures gracefully

**Current state**  
`AIChatWidget` calls `localStorage.getItem` / `localStorage.setItem` directly. In private-browsing / incognito mode on some browsers, these throw `SecurityError`. The entire widget becomes non-functional silently.

Similarly, `useNewsStore` calls `localStorage.setItem` in several paths without accounting for the throw.

**Target state**  
Create `frontend/src/utils/storage.ts`:
```typescript
/**
 * Safe localStorage wrapper that degrades gracefully in private-browsing mode.
 * All write failures are caught and logged; reads return null on failure.
 */
export const safeStorage = {
  get(key: string): string | null {
    try {
      return localStorage.getItem(key)
    } catch {
      return null
    }
  },
  set(key: string, value: string): void {
    try {
      localStorage.setItem(key, value)
    } catch {
      // Private browsing or quota exceeded — fail silently
    }
  },
  remove(key: string): void {
    try {
      localStorage.removeItem(key)
    } catch {
      // ignore
    }
  },
}
```

Replace all direct `localStorage` calls in both files with `safeStorage`.

**Files:**  
- Create `frontend/src/utils/storage.ts`  
- `frontend/src/components/AIChatWidget.vue` — `getRateLimitRemaining` and `setRateLimitTimestamp` functions  
- `frontend/src/composables/useNewsStore.ts` — `hydrateStore`, `setArticles`, `prependArticle`, `updateArticle`  
- `frontend/src/views/DashboardView.vue` — `getInitialLayout`, `saveLayout`

---

### 5.3 — Make the `TerminalStatusBar` sidebar-aware

**Current state**  
The status bar uses `left-0 right-0` and spans the full viewport width, including the sidebar area, which creates a visual misalignment — the bar's left edge does not align with the main content column.

**Target state**  
Bind the bar's `left` offset to the sidebar's computed width using a CSS variable injected by `App.vue`:

```typescript
// In App.vue script:
const sidebarWidth = computed(() =>
  sidebarCollapsed.value ? '80px' : '288px'   // lg:w-20 → 80px, lg:w-72 → 288px
)
```

```html
<!-- In App.vue template, on the root authenticated div: -->
<div
  class="flex h-screen w-screen overflow-hidden ..."
  :style="{
    '--sidebar-width': sidebarWidth,
    '--active-brand-color': activeBrandColor,
    '--active-brand-color-glow': activeBrandColorGlow,
  }"
>
```

```html
<!-- In TerminalStatusBar.vue — add left offset on lg breakpoint: -->
<div
  class="fixed bottom-0 right-0 z-40 h-6 flex items-center ..."
  :style="{ left: 'var(--sidebar-width, 0px)' }"
>
```

This makes the bar track the sidebar width automatically with no JavaScript resize observers.

**Files:**  
- `frontend/src/App.vue` — computed `sidebarWidth`, root div `:style` binding  
- `frontend/src/components/TerminalStatusBar.vue` — root element `:style` binding (line ~40)

---

### 5.4 — Remove unused `conftest.py` path and clean `pytest.ini`

**Current state**  
`pytest.ini` has only `filterwarnings`. There is no `conftest.py` at the project root, which means the `anyio` test mode is not configured and the `backend/` package root is not on `sys.path` during test collection.

**Target state**  
Create `backend/conftest.py`:
```python
"""
Pytest configuration for the backend test suite.

Sets anyio mode to asyncio for all @pytest.mark.anyio tests,
and ensures the backend package is importable from the project root.
"""
import pytest


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
```

Update `pytest.ini`:
```ini
[pytest]
testpaths = backend/app/tests
asyncio_mode = auto
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

**Files:**  
- Create `backend/conftest.py`  
- `pytest.ini` — add `testpaths` and `asyncio_mode`

---

## Implementation Order & Dependency Graph

```
Phase 1 (bugs)
    └── must complete before any refactoring
Phase 2 (config)
    └── must complete before Phase 3 (consuming modules need new Settings fields)
Phase 3 (backend arch)
    ├── 3.1 (ASSET_REGEX) depends on Phase 2 (settings consumed) + handlers/config changes
    ├── 3.2 (caching) is independent
    ├── 3.3 (mutable state) depends on Phase 2 (settings.LLM_MAX_BACKGROUND_RPM)
    └── 3.4 (lazy imports) is independent
Phase 4 (frontend)
    ├── 4.1 (env constants) is independent — do first
    ├── 4.4 (asset constants) depends on 4.2 (RouteAssetId broadening)
    └── 4.5 (vite-env.d.ts) enables type-checking for 4.1
Phase 5 (UI/UX)
    └── independent of Phases 1–4, can run in parallel
```

---

## Verification Checklist

After completing all phases, validate with:

```bash
# Backend
cd backend
python -m ruff check app --fix
python -m ruff format app
python -m mypy --strict --explicit-package-bases backend/app/
python -m pytest backend/app/tests/ -v

# Frontend
cd frontend
npx vue-tsc --noEmit
npm run build
```

Expected outcome: **zero warnings, zero type errors, all tests green.**
