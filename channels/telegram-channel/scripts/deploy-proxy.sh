#!/usr/bin/env bash
set -euo pipefail

# Deploys a tiny Telegram API proxy on EC2 (t3.micro, free tier eligible).
# Usage: ./scripts/deploy-proxy.sh [--teardown]

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
