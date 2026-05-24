# Solana Quant Bot Funding

Scripts for funding the Solana Quant Bot wallet and verifying balances.

## Initial Funding

```bash
# Dry run first
./fund-bot-wallet.sh --amount 50 --from-wallet <YOUR_WALLET> --namespace customer1 --dry-run

# Execute funding
./fund-bot-wallet.sh --amount 50 --from-wallet <YOUR_WALLET> --namespace customer1

# Verify balance after
./fund-bot-wallet.sh --bot-wallet <BOT_ADDRESS> --verify
```

## Options

| Option | Description |
|--------|-------------|
| `--amount SOL` | Amount in SOL to fund (default: 50) |
| `--from-wallet ADDR` | Source wallet (required for transfers) |
| `--bot-wallet ADDR` | Bot wallet (auto-read from K8s secret if omitted) |
| `--namespace NS` | K8s namespace (default: customer1) |
| `--dry-run` | Simulate without sending |
| `--verify` | Check bot wallet balance |

## Security Notes

- The bot wallet private key is stored as a SOPS-encrypted K8s secret.
- Initial funding should use a dedicated hot wallet, not a multi-sig for simplicity.
- sec-ops may require multi-sig for larger seed amounts.
- Monitor the bot wallet for anomalous transactions via the Prometheus alerts.
