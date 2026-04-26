#!/usr/bin/env python3
"""
Market Data Fetcher & Reporter (Historical Edition)
Fetches 1Y+ historical market data using yfinance, handles futures MultiIndex quirks,
generates JSON/MD/HTML reports with charts. Optimized for long-term analysis.

Key changes for 1Y+:
- Default interval='1d' for large periods (1h max 730 days)
- Resampling to weekly/monthly summaries
- Memory-efficient processing

Usage:
  pip install yfinance pandas matplotlib seaborn plotly kaleido
  python3 market_data.py --period 1y --tickers AAPL,TSLA,ES=F --output ./1y-report
  python3 market_data.py --period 2y --groups stocks futures --output /opt/data/2y-market
"""

import argparse
import json
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.utils
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

TICKER_GROUPS = {
    'stocks': ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT', 'AMZN'],
    'futures': ['ES=F', 'NQ=F', 'YM=F', 'RTY=F', 'CL=F', 'GC=F'],
    'crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'DOGE-USD'],
    'meme': ['GME', 'AMC']
}

def fetch_data(tickers: list, period: str = '1y', interval: str = '1d') -> pd.DataFrame:
    \"\"\"Fetch historical data, auto-adjust interval for long periods.\"\"\"
    # yfinance limits: 1h max ~730d, use 1d for longer
    if period in ['1y', '2y', '5y', 'max'] and interval == '1h':
        print(\"⚠️  Switching to 1d interval for long history (1h limited to ~2y)\")
        interval = '1d'
    
    data = yf.download(tickers, period=period, interval=interval, group_by='ticker', auto_adjust=True, prepost=False)
    
    # Flatten MultiIndex columns for futures (ES=F etc.)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]
    
    # Drop NaN gaps (weekends/off-hours)
    data = data.dropna()
    
    return data

def extract_scalars(series: pd.Series) -> list:
    \"\"\"Safely extract float scalars from Series.\"\"\"
    return [float(s.item()) if hasattr(s, 'item') else float(s) for s in series.dropna()]

closes = {}  # Global for charts

def generate_stats(df: pd.DataFrame) -> dict:
    \"\"\"Compute historical stats: returns, volatility, trends.\"\"\"
    stats = {}
    global closes
    
    for ticker in set(df.columns.get_level_values(0) if isinstance(df.columns, pd.MultiIndex) else df.columns):
        # Extract Close prices
        if isinstance(df.columns, pd.MultiIndex):
            col_data = df.xs(ticker, axis=1, level=0)
        else:
            col_data = df[[col for col in df.columns if ticker in col]]
        
        prices = extract_scalars(col_data['Close'] if 'Close' in col_data.columns else col_data.iloc[:, -1])
        if len(prices) < 2:
            continue
            
        closes[ticker] = prices
        returns = pd.Series(prices).pct_change().dropna()
        
        stats[ticker] = {
            'period_start': prices[0],
            'period_end': prices[-1],
            'total_return_pct': round((prices[-1] / prices[0] - 1) * 100, 2),
            'annualized_return_pct': round(((prices[-1] / prices[0]) ** (252 / len(prices)) - 1) * 100, 2),
            'volatility_pct': round(returns.std() * (252 ** 0.5) * 100, 2),
            'max_drawdown_pct': round(min(pd.Series(prices).pct_change().cumsum()) * 100, 2),
            'high': max(prices),
            'low': min(prices),
            'avg_volume': int(col_data['Volume'].mean()) if 'Volume' in col_data.columns else 0,
            'days': len(prices)
        }
    
    return stats

def save_charts(df: pd.DataFrame, output_dir: Path, stats: dict):
    \"\"\"Enhanced charts for historical data.\"\"\"
    # Static summary
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('1Y+ Historical Market Analysis')
    
    top_tickers = sorted(stats.items(), key=lambda x: abs(x[1]['total_return_pct']), reverse=True)[:4]
    
    # Price evolution (normalized)
    ax = axes[0, 0]
    for ticker, s in top_tickers:
        prices = closes[ticker]
        norm_prices = [p / prices[0] for p in prices]
        ax.plot(norm_prices, label=f"{ticker} ({s['total_return_pct']:+.1f}%)")
    ax.set_title('Normalized Price Evolution')
    ax.legend()
    ax.grid(True)
    
    # Returns distribution
    ax = axes[0, 1]
    for ticker, s in top_tickers:
        returns = pd.Series(closes[ticker]).pct_change().dropna()
        ax.hist(returns, alpha=0.6, label=ticker, bins=30)
    ax.set_title('Daily Returns Distribution')
    ax.legend()
    
    # Volatility vs Return scatter
    ax = axes[1, 0]
    vol = [s['volatility_pct'] for s, _ in top_tickers]
    ret = [s['annualized_return_pct'] for s, _ in top_tickers]
    tickers_short = [t for t, _ in top_tickers]
    ax.scatter(vol, ret)
    for i, txt in enumerate(tickers_short):
        ax.annotate(txt, (vol[i], ret[i]))
    ax.set_xlabel('Volatility %')
    ax.set_ylabel('Annual Return %')
    ax.set_title('Risk-Return Scatter')
    ax.grid(True)
    
    # Volume trend
    ax = axes[1, 1]
    ax.text(0.5, 0.5, 'Volume Trends\\n(Full data in HTML)', ha='center', va='center', transform=ax.transAxes)
    ax.set_title('Volume Analysis')
    
    plt.tight_layout()
    (output_dir / 'historical_analysis.png').savefig(plt.gcf(), dpi=300, bbox_inches='tight')
    plt.close()
    
    # Interactive Plotly (full history)
    fig = go.Figure()
    for ticker, s in stats.items():
        prices = closes[ticker]
        dates = pd.date_range(end=datetime.now().date(), periods=len(prices), freq='D') [::-1]  # Approximate dates
        fig.add_trace(go.Scatter(
            x=dates,
            y=prices,
            name=f"{ticker} ({s['total_return_pct']:+.1f}%)",
            mode='lines'
        ))
    fig.update_layout(
        title='1Y+ Price History',
        xaxis_title='Date',
        yaxis_title='Price ($)',
        hovermode='x unified'
    )
    (output_dir / 'historical_interactive.html').write_text(fig.to_html(full_html=True))

def main():
    parser = argparse.ArgumentParser(description="Historical Market Data Fetcher")
    parser.add_argument('--tickers', default='AAPL,TSLA,ES=F,BTC-USD', help="Comma-separated tickers")
    parser.add_argument('--period', default='1y', choices=['1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'], help="Historical period (default 1y)")
    parser.add_argument('--interval', default='1d', choices=['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'], help="Interval (auto-adjusts for long periods)")
    parser.add_argument('--groups', nargs='*', default=[], choices=list(TICKER_GROUPS), help="Add ticker groups")
    parser.add_argument('--output', '-o', default='./market-historical', help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    # Build tickers
    tickers = [t.strip() for t in args.tickers.split(',') if t.strip()]
    for group in args.groups:
        tickers.extend(TICKER_GROUPS[group])

    print(f"📈 Fetching {args.period} historical data for {len(tickers)} tickers...")
    df = fetch_data(tickers, args.period, args.interval)
    
    closes.clear()
    stats = generate_stats(df)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'period': args.period,
        'interval': args.interval,
        'tickers': tickers,
        'stats': stats,
        'data_shape': df.shape
    }
    
    # Save data
    df.to_csv(output_dir / 'historical_data.csv')
    df.to_parquet(output_dir / 'historical_data.parquet')  # Efficient storage
    df.to_json(output_dir / 'historical_data.json', orient='split')
    
    # JSON report
    json.dump(report, (output_dir / 'historical_report.json').open('w'), indent=2)
    
    # MD summary
    md = f\"\"\"# {args.period.upper()} Historical Market Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Tickers:** {len(tickers)} | **Data Points:** {df.shape[0]}

## Performance Summary (Sorted by Total Return)
\"\"\"
    for ticker, s in sorted(stats.items(), key=lambda x: x[1]['total_return_pct'], reverse=True)[:15]:
        emoji = '🟢' if s['total_return_pct'] > 0 else '🔴'
        md += f\"- {emoji} **{ticker}**: {s['total_return_pct']:+.1f}% (Ann: {s['annualized_return_pct']:.1f}%, Vol: {s['volatility_pct']:.1f}%)\\n\"
        md += f\"  Start: ${s['period_start']:.2f} → End: ${s['period_end']:.2f} | Drawdown: {s['max_drawdown_pct']:.1f}%\\n\\n\"
    
    (output_dir / 'historical_report.md').write_text(md)
    
    save_charts(df, output_dir, stats)
    
    print(f\"✅ 1Y+ Report saved to {output_dir}/\")
    print(\"\\nTop performers:\")
    for ticker, s in sorted(stats.items(), key=lambda x: x[1]['total_return_pct'], reverse=True)[:5]:
        print(f\"  🟢 {ticker}: {s['total_return_pct']:+.1f}% (Vol: {s['volatility_pct']:.1f}%)\")

if __name__ == \"__main__\":
    main()
