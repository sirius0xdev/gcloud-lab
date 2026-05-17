#!/bin/bash
# =============================================================================
# Manual mTLS certificate generation script (for dev/testing only)
# =============================================================================
# In production, use cert-manager (see k8s/base/cert-manager/).
# This script generates self-signed certificates for local testing.
#
# Usage:
#   ./deploy/scripts/generate-mtls-certs.sh
#
# Output: deploy/mtls/
# =============================================================================

set -euo pipefail

OUTPUT_DIR="deploy/mtls"
SERVICES=("execute-service" "data-service" "news-service" "api-gateway" "dashboard")
DAYS_VALID=365

mkdir -p "$OUTPUT_DIR/ca" "$OUTPUT_DIR/certs"

# ── Generate Root CA ────────────────────────────────────────────────────────
echo "Generating Root CA..."
openssl genrsa -out "$OUTPUT_DIR/ca/ca.key" 4096 2>/dev/null
openssl req -x509 -new -nodes \
  -key "$OUTPUT_DIR/ca/ca.key" \
  -sha256 \
  -days $DAYS_VALID \
  -out "$OUTPUT_DIR/ca/ca.crt" \
  -subj "/C=US/ST=California/O=TradingPlatform/CN=Trading Platform Root CA"

# ── Generate Service Certificates ────────────────────────────────────────────
for SERVICE in "${SERVICES[@]}"; do
  echo "Generating certificate for $SERVICE..."

  # Generate private key
  openssl genrsa \
    -out "$OUTPUT_DIR/certs/${SERVICE}.key" 2048 2>/dev/null

  # Generate CSR
  openssl req -new \
    -key "$OUTPUT_DIR/certs/${SERVICE}.key" \
    -out "$OUTPUT_DIR/certs/${SERVICE}.csr" \
    -subj "/C=US/ST=California/O=TradingPlatform/CN=${SERVICE}.customer1.svc.cluster.local" \
    -addext "subjectAltName=DNS:${SERVICE},DNS:${SERVICE}.customer1,DNS:${SERVICE}.customer1.svc.cluster.local"

  # Sign with CA
  openssl x509 -req \
    -in "$OUTPUT_DIR/certs/${SERVICE}.csr" \
    -CA "$OUTPUT_DIR/ca/ca.crt" \
    -CAkey "$OUTPUT_DIR/ca/ca.key" \
    -CAcreateserial \
    -out "$OUTPUT_DIR/certs/${SERVICE}.crt" \
    -days $DAYS_VALID \
    -sha256 \
    -extfile <(printf "subjectAltName=DNS:${SERVICE},DNS:${SERVICE}.customer1,DNS:${SERVICE}.customer1.svc.cluster.local")

  # Clean up CSR
  rm "$OUTPUT_DIR/certs/${SERVICE}.csr"
done

echo "Done! All certificates generated in $OUTPUT_DIR/certs/"
echo "CA certificate: $OUTPUT_DIR/ca/ca.crt"
echo ""
echo "To verify a certificate:"
echo "  openssl verify -CAfile $OUTPUT_DIR/ca/ca.crt $OUTPUT_DIR/certs/<service>.crt"
