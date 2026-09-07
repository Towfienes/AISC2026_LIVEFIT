# LiveLift web (Next.js control desk) — multi-stage build.
# Build context: ./web (see docker-compose.yml: context ./web, dockerfile ../docker/web.Dockerfile).

# --- deps: install exact locked dependencies ---
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- build: compile the production bundle ---
FROM node:20-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
# NEXT_PUBLIC_* is inlined into the client bundle AT BUILD TIME, so the API
# base must arrive here as build args (docker-compose.yml passes them from
# .env). Default: through the caddy gateway at /api.
ARG NEXT_PUBLIC_API_URL=http://localhost/api
ARG NEXT_PUBLIC_PUBLIC_API_BASE=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Ensure public/ exists so the runner COPY below never fails. An EMPTY
# NEXT_PUBLIC_PUBLIC_API_BASE must stay undefined (api.ts falls back with ??),
# so unset it instead of inlining "".
RUN mkdir -p public \
    && if [ -z "${NEXT_PUBLIC_PUBLIC_API_BASE:-}" ]; then unset NEXT_PUBLIC_PUBLIC_API_BASE; fi \
    && npm run build

# --- runner: minimal production server ---
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/public ./public
COPY --from=build /app/.next ./.next
USER node
EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000"]
