# ──────────────────────────────────────────────────────────────────────────────
# Stage 1: Build — compile the Vue 3 / Vite application bundle.
#
# Uses npm ci (clean install) instead of npm install for reproducible,
# deterministic dependency resolution from package-lock.json.
# ──────────────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS build-stage

WORKDIR /app

# Install dependencies first in a dedicated layer so the cache is preserved
# when only source files change.
COPY package.json package-lock.json ./
RUN npm ci --prefer-offline

# Copy source assets and compile the production bundle.
COPY . .
RUN npm run build

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2: Production serve — ultra-slim Nginx image with only the built assets.
#
# nginx:alpine-slim is ~12 MB — no Node.js runtime or dev tooling is present.
# ──────────────────────────────────────────────────────────────────────────────
FROM nginx:alpine-slim AS production-stage

# Custom Nginx config for SPA history-mode routing and gzip compression.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled build assets from the builder stage only.
COPY --from=build-stage /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
