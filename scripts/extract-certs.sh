#!/bin/bash
set -eo pipefail

ACME_JSON="/home/homeserver/mediaserver/config/traefik/acme.json"
CERT_DIR="/home/homeserver/mediaserver/config/adguard/certs"
DOMAIN="dns.erwanleboucher.dev"

mkdir -p "$CERT_DIR"

if command -v jq &> /dev/null && [ -f "$ACME_JSON" ]; then
    jq -r ".myresolver.Certificates[] | select(.domain.main==\"$DOMAIN\") | .certificate" "$ACME_JSON" | base64 -d > "$CERT_DIR/cert.pem"
    jq -r ".myresolver.Certificates[] | select(.domain.main==\"$DOMAIN\") | .key" "$ACME_JSON" | base64 -d > "$CERT_DIR/key.pem"

    chmod 600 "$CERT_DIR/key.pem"
    echo "Certs extracted for $DOMAIN"
else
    echo "acme.json not found or jq not installed"
    exit 1
fi
