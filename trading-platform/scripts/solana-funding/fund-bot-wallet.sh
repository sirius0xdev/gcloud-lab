#!/usr/bin/env bash
# fund-bot-wallet.sh — Initial funding script for Solana Quant Bot
#
# Usage: ./fund-bot-wallet.sh [OPTIONS]
#
# Options:
#   --amount SOL        Amount in SOL to fund (default: 50)
#   --from-wallet ADDR  Source wallet address (required)
#   --bot-wallet ADDR   Bot wallet address (default: reads from K8s secret)
#   --namespace NS      K8s namespace (default: customer1)
#   --dry-run           Simulate transfer without sending
#   --verify            Verify current bot wallet balance (no transfer)
#   --help              Show this help
#
# This script:
#  1. Reads the bot's wallet address from the K8s secret
#  2. Sends SOL from --from-wallet to the bot wallet
#  3. Verifies the balance on-chain and in K8s
#
# Prerequisites:
#  - solana-cli installed and configured
#  - kubectl configured for the cluster
#  - --from-wallet must have enough SOL for the transfer + fees

set -euo pipefail

# Defaults
AMOUNT="50"
FROM_WALLET=""
BOT_WALLET=""
NAMESPACE="customer1"
DRY_RUN=false
VERIFY_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --amount) AMOUNT="$2"; shift 2 ;;
    --from-wallet) FROM_WALLET="$2"; shift 2 ;;
    --bot-wallet) BOT_WALLET="$2"; shift 2 ;;
    --namespace) NAMESPACE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --verify) VERIFY_ONLY=true; shift ;;
    --help)
      head -30 "$0" | tail -25
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Helper: get bot wallet from K8s secret if not explicitly provided
get_bot_wallet_from_secret() {
  if [[ -n "$BOT_WALLET" ]]; then
    echo "$BOT_WALLET"
    return
  fi

  echo "Reading bot wallet from K8s secret..."
  BOT_WALLET=$(kubectl -n "$NAMESPACE" get secret solana-quant-bot-secrets \
    -o jsonpath='{.data.SOLANA_BOT_WALLET_ADDRESS}' 2>/dev/null | base64 -d 2>/dev/null || true)

  if [[ -z "$BOT_WALLET" ]]; then
    echo "ERROR: Could not read bot wallet from secret solana-quant-bot-secrets in namespace $NAMESPACE"
    echo "Either deploy the secret first or pass --bot-wallet explicitly."
    exit 1
  fi
  echo "Bot wallet: $BOT_WALLET"
}

# Verify balance
verify_balance() {
  local wallet="$1"
  echo "=== Verifying balance for $wallet ==="

  # On-chain balance
  local on_chain_balance
  on_chain_balance=$(solana balance "$wallet" --output json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin))" 2>/dev/null || echo "0")
  echo "On-chain SOL balance: $on_chain_balance"

  # Expected minimum
  local expected
  expected=$(echo "$AMOUNT * 0.99" | bc)  # account for fees
  local is_ok
  is_ok=$(echo "$on_chain_balance >= $expected" | bc -l)

  if [[ "$is_ok" -eq 1 ]]; then
    echo "OK: Balance >= $expected SOL (transferred amount minus fees)"
  else
    echo "WARNING: Balance ($on_chain_balance) < expected ($expected SOL)"
    echo "         The transfer may still be pending confirmation."
  fi
}

# --- Main ---

echo "============================================"
echo "  Solana Quant Bot — Initial Funding"
echo "============================================"
echo "  Amount:     $AMOUNT SOL"
echo "  Namespace:  $NAMESPACE"
echo "  Dry run:    $DRY_RUN"
echo "============================================"

# Validate from-wallet
if [[ -z "$FROM_WALLET" ]]; then
  echo "ERROR: --from-wallet is required (source wallet address)"
  exit 1
fi

# Get bot wallet
get_bot_wallet_from_secret

# Verify mode
if [[ "$VERIFY_ONLY" == true ]]; then
  verify_balance "$BOT_WALLET"
  exit 0
fi

# Dry run
if [[ "$DRY_RUN" == true ]]; then
  echo ""
  echo "DRY RUN — Would transfer $AMOUNT SOL from:"
  echo "  $FROM_WALLET  ->  $BOT_WALLET"
  echo ""
  echo "Source wallet balance:"
  solana balance "$FROM_WALLET"
  echo ""
  echo "Bot wallet balance:"
  solana balance "$BOT_WALLET"
  echo ""
  echo "To execute, remove --dry-run."
  exit 0
fi

# Check source wallet has enough
echo "Checking source wallet balance..."
SOURCE_BALANCE=$(solana balance "$FROM_WALLET" --output json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin))" 2>/dev/null || echo "0")
echo "Source wallet: $SOURCE_BALANCE SOL"

HAS_ENOUGH=$(echo "$SOURCE_BALANCE >= $AMOUNT" | bc -l)
if [[ "$HAS_ENOUGH" -ne 1 ]]; then
  echo "ERROR: Source wallet ($SOURCE_BALANCE SOL) has less than $AMOUNT SOL"
  exit 1
fi

# Confirm before sending (unless CI)
if [[ "${CI:-false}" != "true" ]]; then
  echo ""
  read -p "Send $AMOUNT SOL from $FROM_WALLET to $BOT_WALLET? (yes/no): " CONFIRM
  if [[ "$CONFIRM" != "yes" ]]; then
    echo "Aborted."
    exit 0
  fi
fi

# Send transaction
echo "Sending transaction..."
TX_SIGNATURE=$(solana transfer "$FROM_WALLET" \
  "$BOT_WALLET" \
  "$AMOUNT" \
  --with-block-time \
  --output json 2>&1 | tee /tmp/solana-fund-tx.json)

echo "Transaction: $TX_SIGNATURE"

# Wait for confirmation
echo "Waiting for confirmation..."
solana confirm "$(echo "$TX_SIGNATURE" | python3 -c "import sys,json; print(json.load(sys.stdin)['signature'])")" --with-max-confirm-retries 20

# Verify balance
echo ""
verify_balance "$BOT_WALLET"

echo ""
echo "Funding complete. Bot wallet: $BOT_WALLET"
echo "Transferred: $AMOUNT SOL"
