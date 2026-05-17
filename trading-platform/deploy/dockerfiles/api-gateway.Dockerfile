# =============================================================================
# API Gateway Dockerfile — Nginx-based reverse proxy with rate limiting
# =============================================================================
FROM nginx:1.25-alpine AS production

# Copy custom nginx configuration
COPY deploy/k8s/base/gateway/nginx.conf /etc/nginx/nginx.conf
COPY deploy/k8s/base/gateway/conf.d/ /etc/nginx/conf.d/

# Create required directories
RUN mkdir -p /etc/nginx/ssl \
    /etc/nginx/conf.d \
    /var/cache/nginx \
    /var/run/nginx \
    /var/log/nginx \
    && touch /var/run/nginx/nginx.pid

# Security: run as nginx user (already exists in alpine image)
USER nginx

EXPOSE 8080 8443

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
