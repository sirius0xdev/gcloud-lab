# =============================================================================
# mTLS Configuration for Trading Platform
# =============================================================================
# This directory contains certificates and configuration for mutual TLS
# between services. In production, use cert-manager to automate this.
#
# Option 1: cert-manager (recommended for production)
# Option 2: Manual certificate management (for dev/testing)
#
# Certificate hierarchy:
#   Root CA
#   ├── Service CA (issues service-to-service certs)
#   │   ├── execute-service cert
#   │   ├── data-service cert
#   │   ├── news-service cert
#   │   ├── api-gateway cert
#   │   └── dashboard cert
#   └── Ingress CA (for external-facing TLS)
#       └── api-gateway TLS cert (for HTTPS)
# =============================================================================
