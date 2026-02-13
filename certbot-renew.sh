#!/bin/sh

# Certbot Certificate Renewal Script
# Runs continuously and checks for certificate renewals every 12 hours.
# Let's Encrypt certificates are valid for 90 days and are renewed
# when they have less than 30 days remaining.

set -e

echo "Certbot automatic renewal service started"
echo "Checking for certificate renewals every 12 hours..."

# Trap TERM signal for graceful shutdown
trap 'echo "Received TERM signal, exiting..."; exit 0' TERM

CERT_CHECK_INTERVAL=30
MAX_CERT_WAIT=600

# Wait for initial certificates before starting renewal loop
echo "Waiting for valid Let's Encrypt certificates to be created..."
WAIT_TIME=0

while [ $WAIT_TIME -lt $MAX_CERT_WAIT ]; do
    CERT_OUTPUT=$(certbot certificates 2>/dev/null)

    if echo "$CERT_OUTPUT" | grep -q "Certificate Name"; then
        echo "$(date): Found certbot-managed certificates, starting renewal monitoring"
        break
    fi

    if [ $WAIT_TIME -ge $MAX_CERT_WAIT ]; then
        echo "$(date): No certbot-managed certificates found after waiting $MAX_CERT_WAIT seconds"
        echo "$(date): Continuing anyway - renewal checks will be performed but may fail until certificates are obtained"
        break
    fi

    echo "$(date): No certbot-managed certificates found yet, waiting... ($WAIT_TIME/$MAX_CERT_WAIT seconds)"
    sleep $CERT_CHECK_INTERVAL
    WAIT_TIME=$((WAIT_TIME + CERT_CHECK_INTERVAL))
done

# Main renewal loop
while :; do
    echo "$(date): Checking for certificate renewals..."

    if certbot renew --webroot -w /var/www/letsencrypt --quiet; then
        echo "$(date): Certificate renewal check completed successfully"
    else
        echo "$(date): Certificate renewal check failed (normal if certificates don't need renewal yet)"
    fi

    # Sleep for 12 hours, but allow interruption by TERM signal
    sleep 43200 & wait $!
done
