# =============================================================================
# Dashboard Dockerfile — Next.js multi-stage build with static export
# =============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (better layer caching)
COPY trading-platform/dashboard/package*.json ./
RUN npm ci

# Copy source and build
COPY trading-platform/dashboard/ ./
RUN npm run build

# Production stage
FROM node:20-alpine AS production

# Security: non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

WORKDIR /app

# Copy built output and package.json from builder
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

USER nextjs

EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
