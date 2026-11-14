# =============================================================================
# RestaurantFlow — Frontend Dockerfile (multi-stage)
# Phase 23: Production-ready Nginx-served SPA
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: builder — compile React/Vite app
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_URL
ARG VITE_WS_URL
ARG VITE_APP_NAME

RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: runtime — Nginx serves the static bundle
# -----------------------------------------------------------------------------
FROM nginx:alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY deployment/nginx/nginx-spa.conf /etc/nginx/conf.d/default.conf

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
