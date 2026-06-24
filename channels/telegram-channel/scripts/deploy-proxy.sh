#!/usr/bin/env bash
set -euo pipefail

# Deploys a tiny Telegram API proxy on EC2 (t3.micro, free tier eligible).
# Usage: ./scripts/deploy-proxy.sh [--teardown]
#
# Why this is here
# ----------------
# Some networks (corporate firewalls, certain country-level filters) block
# api.telegram.org. The widely-documented workaround is to stand up an HTTP
# reverse-proxy on a network that can reach Telegram, then point the bot at
# the proxy. Telegram itself documents this pattern (MTProto + HTTP relays)
# and it is reproduced in dozens of public repos and tutorials. Nothing in
# this script is a non-public technique.
#
# Use at your own risk
# --------------------
# - The CloudFormation template opens port 80 to 0.0.0.0/0. Anyone who finds
#   the proxy URL can route their own Telegram traffic through it and your AWS
#   account picks up the bill. Lock the SecurityGroup down to your own egress
#   CIDR before any non-demo use.
# - No TLS in the default template. Tokens transit in plaintext between the
#   bot and the proxy. Front it with ALB + ACM (or terminate TLS on the
#   instance via Let's Encrypt) before sending real credentials.
# - Standing up a proxy to bypass a corporate firewall may violate your
#   employer's acceptable-use policy. Check first.
# - Always run `--teardown` when finished. AWS bills idle EC2 the same as
#   busy EC2, and an abandoned open relay is a liability.

STACK_NAME="ark-telegram-proxy"
REGION="${AWS_REGION:-us-east-1}"

if [[ "${1:-}" == "--teardown" ]]; then
    echo "Tearing down ${STACK_NAME}..."
    aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
    aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION"
    echo "Done."
    exit 0
fi

echo "Deploying Telegram API proxy to AWS ($REGION)..."

aws cloudformation deploy \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --template-file "$(dirname "$0")/proxy-cfn.yaml" \
    --capabilities CAPABILITY_IAM \
    --no-fail-on-empty-changeset

PROXY_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ProxyUrl`].OutputValue' \
    --output text)

echo ""
echo "============================================================"
echo "Telegram API proxy is running!"
echo ""
echo "  Proxy URL: ${PROXY_URL}"
echo ""
echo "  To use it:"
echo "    export TELEGRAM_API_BASE='${PROXY_URL}/bot'"
echo "    export TELEGRAM_BOT_TOKEN='your-token'"
echo "    make dev"
echo ""
echo "  To tear down:"
echo "    ./scripts/deploy-proxy.sh --teardown"
echo "============================================================"
