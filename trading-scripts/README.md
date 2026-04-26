# Trading Scripts: Market Data Fetcher

Historical market data pipeline for AI analysis. Fetches stocks/futures/crypto, computes stats/charts, exports for uncensored LLMs.

## 🚀 Quick Start

```bash
# Install deps (one-time)
pip install yfinance pandas matplotlib seaborn plotly kaleido pyarrow

# Basic 1Y report
python market_data.py --period 1y --groups stocks futures crypto --output ./report-1y

# Live daily movers
python market_data.py --period 1d --groups meme --output ./today-movers
```

## 📊 Features

- **1Y+ History** (auto-adjusts interval: 1d for long periods)
- **Futures-safe** (flattens MultiIndex for ES=F etc., drops NaN gaps)
- **Stats:** Total/annual returns, volatility, max drawdown, volume
- **Exports:** CSV/Parquet/JSON + PNG charts + interactive HTML
- **Groups:** `stocks` (AAPL/TSLA), `futures` (ES=F/NQ=F), `crypto` (BTC-USD), `meme` (GME)

## Usage

```bash
python market_data.py [OPTIONS]

Options:
  --tickers AAPL,TSLA,ES=F     Comma-separated (default: AAPL,TSLA,ES=F,BTC-USD)
  --period 1y                  1mo|3mo|6mo|1y|2y|5y|10y|ytd|max (default: 1y)
  --interval 1d                1m|5m|1h|1d|1wk (auto-adjusts)
  --groups stocks futures      Add predefined groups
  --output ./reports           Output dir (default: ./market-historical)
```

## Examples

**Retail Biz Demo:**
```bash
python market_data.py --period 1y --tickers AAPL,TSLA --output retail-stocks
# Feed report JSON to uncensored bot: "Analyze TSLA for landscaping firm cashflow"
```

**Daily Alerts (Cron):**
```bash
# Save daily to /opt/data/market-daily
0 9 * * 1-5 python /opt/gcloud-lab/trading-scripts/market_data.py --period 1d --output /opt/data/market-daily/today
```

**Meme Stocks Live:**
```bash
python market_data.py --period 5d --groups meme --interval 1h --output meme-watch
```

## Outputs

```
report/
├── historical_data.csv          # Raw OHLCV
├── historical_data.parquet      # Efficient (AI load: pd.read_parquet)
├── historical_report.json       # Stats summary
├── historical_report.md         # Human-readable
├── historical_analysis.png      # Charts (normalized prices, returns, risk-return)
└── historical_interactive.html  # Zoomable Plotly
```

## AI Integration (OpenClaw/Uncensored Bots)

```python
import json
with open('report/historical_report.json') as f:
    data = json.load(f)

prompt = f"Analyze these 1Y stats for retail biz: {json.dumps(data['stats'])}"
# POST to vLLM: http://openclaw-brain-service:8000/v1/chat/completions
```

## Troubleshooting

- **No data:** Check market hours (futures/crypto 24/7)
- **MultiIndex error:** Auto-handled (memory quirk fixed)
- **Large files:** Use `--period 1mo` or Parquet
- **Deps:** `pyarrow` for Parquet read/write

**For clients:** "Uncensored AI stock insights — privacy-first, no filters."

---
*Built for gcloud-lab OpenClaw Brain. FluxCD deploys ready.*
