#!/usr/bin/env python3
"""
ORB (Opening Range Breakout) Monitor for Futures
=================================================

Monitors session opens across global markets and detects ORB signals.

Sessions monitored (ET / UTC-4):
  • Asia (Tokyo)   — 19:00 ET  (23:00 UTC)
  • London         — 03:00 ET  (07:00 UTC)
  • New York       — 09:30 ET  (13:30 UTC)

Strategy: After the session opens, the opening range high/low is captured
over `range_minutes`. If price later breaks above/below that range, an
ORB signal is logged.

⚠️  EDUCATIONAL PURPOSE ONLY — Not financial advice.
    Uses yfinance (delayed data). NOT suitable for live trading.
"""

from __future__ import annotations

import sys
import logging
from datetime import datetime, timedelta, timezone

import yaml
import pandas as pd
import yfinance as yf

# ─── Constants ────────────────────────────────────────────────────────────────

# Yahoo Finance futures tickers
SYMBOLS = {
    "ES": {"ticker": "ES=F",  "name": "S&P 500 E-mini",     "multiplier": 0.25},
    "NQ": {"ticker": "NQ=F",  "name": "Nasdaq 100 E-mini",  "multiplier": 0.25},
    "YM": {"ticker": "YM=F",  "name": "Dow E-mini",         "multiplier": 0.05},
    "CL": {"ticker": "CL=F",  "name": "Crude Oil WTI",      "multiplier": 0.01},
    "GC": {"ticker": "GC=F",  "name": "Gold",               "multiplier": 0.10},
}

# Session open times in UTC (no DST ambiguity)
SESSIONS = {
    "asia":   {"name": "Asia (Tokyo)",   "open_utc": 23,   "offset_min": 0},
    "london": {"name": "London",         "open_utc": 7,    "offset_min": 0},
    "ny":     {"name": "New York",       "open_utc": 13,   "offset_min": 30},
}

UTC = timezone.utc

logger = logging.getLogger("ORB")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_config(path: str = "config.yaml") -> dict:
    """Load YAML configuration."""
    try:
        with open(path) as fh:
            return yaml.safe_load(fh)
    except FileNotFoundError:
        logger.warning("config.yaml not found — using defaults")
        return {}





def session_utc_start(date: datetime, session: dict) -> datetime:
    """Return UTC datetime when this session opens on the given UTC date."""
    return datetime(date.year, date.month, date.day,
                    session["open_utc"], session["offset_min"],
                    tzinfo=UTC)


def fetch_data(ticker: str, days: int = 5) -> pd.DataFrame:
    """Fetch intraday futures data from Yahoo Finance (1-min bars)."""
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    try:
        df = yf.download(ticker, start=start, end=end,
                         interval="1m", progress=False, auto_adjust=True)
        if df.empty:
            logger.warning(f"No data returned for {ticker}")
            return df

        # Flatten MultiIndex columns (yf sometimes returns ('Close', ticker), etc.)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        return df
    except Exception as e:
        logger.error(f"Failed to fetch {ticker}: {e}")
        return pd.DataFrame()


def find_session_bars(df: pd.DataFrame, session_start: datetime,
                      range_minutes: int) -> pd.DataFrame | None:
    """Extract the opening-range bars for a session, if data exists."""
    # Allow ±2 min tolerance for session start
    tolerance = timedelta(minutes=2)
    end_bound = session_start + timedelta(minutes=range_minutes) + tolerance
    mask = (df.index >= session_start - tolerance) & \
           (df.index < end_bound)
    range_bars = df.loc[mask]
    return range_bars if len(range_bars) >= 5 else None  # Need meaningful data


def analyze_orb(symbol_key: str, symbol_info: dict, df: pd.DataFrame,
                session_key: str, session_info: dict,
                cfg_orb: dict, date: datetime) -> list[dict]:
    """Check for ORB signals in the data for a given session date."""
    range_min = cfg_orb.get("range_minutes", 30)
    min_range = cfg_orb.get("min_range_ticks", 4)
    max_range = cfg_orb.get("max_range_ticks", 100)
    multiplier = symbol_info["multiplier"]

    signals: list[dict] = []
    session_start = session_utc_start(date, session_info)

    # Try both start date and day before (in case of overnight sessions)
    for offset in [0, -1]:
        check_date = date + timedelta(days=offset)
        try_start = datetime(check_date.year, check_date.month, check_date.day,
                             session_info["open_utc"], session_info["offset_min"],
                             tzinfo=UTC)
        range_bars = find_session_bars(df, try_start, range_min)
        if range_bars is None:
            continue

        # Opening range high/low — force scalar extraction
        range_high = range_bars["High"].max().item()
        range_low = range_bars["Low"].min().item()
        range_size = range_high - range_low
        range_ticks = range_size / multiplier

        if range_ticks < min_range or range_ticks > max_range:
            continue  # Skip — range too small or too large

        # Look for breakout in remaining data after range period
        # Skip NaN rows and only use real data
        remaining = df.loc[range_bars.index[-1]:].dropna(subset=["Close"])
        if remaining.empty:
            continue

        # Bullish breakout: price closes above range high
        bullish_bars = remaining[remaining["Close"] > range_high]
        if not bullish_bars.empty:
            breakout_time = bullish_bars.index[0]
            breakout_price = float(bullish_bars.loc[breakout_time, "Close"])
            signals.append({
                "symbol": symbol_key,
                "name": symbol_info["name"],
                "session": session_info["name"],
                "direction": "LONG",
                "range_high": round(range_high, 2),
                "range_low": round(range_low, 2),
                "range_size": round(range_size, 2),
                "range_ticks": round(range_ticks, 1),
                "breakout_time": breakout_time,
                "breakout_price": round(breakout_price, 2),
            })

        # Bearish breakout: price closes below range low
        bearish_bars = remaining[remaining["Close"] < range_low]
        if not bearish_bars.empty:
            breakout_time = bearish_bars.index[0]
            breakout_price = float(bearish_bars.loc[breakout_time, "Close"])
            signals.append({
                "symbol": symbol_key,
                "name": symbol_info["name"],
                "session": session_info["name"],
                "direction": "SHORT",
                "range_high": round(range_high, 2),
                "range_low": round(range_low, 2),
                "range_size": round(range_size, 2),
                "range_ticks": round(range_ticks, 1),
                "breakout_time": breakout_time,
                "breakout_price": round(breakout_price, 2),
            })

    return signals


# ─── Main ─────────────────────────────────────────────────────────────────────

def run(date_str: str | None = None, days: int = 5,
        config_path: str = "config.yaml") -> list[dict]:
    """
    Analyze ORB patterns for all sessions and symbols.

    Args:
        date_str: Optional date in YYYY-MM-DD format. If None, uses today.
        days:     How many days of history to fetch.
        config_path: Path to config.yaml.

    Returns:
        List of signal dicts sorted by breakout_time.
    """
    cfg = load_config(config_path)
    cfg_orb = cfg.get("orb", {})

    target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC) if date_str else datetime.now(UTC)
    # Expand search window to cover all sessions around the target date
    search_dates = [target_date + timedelta(days=d) for d in range(-1, days)]

    all_signals: list[dict] = []
    symbol_items = cfg.get("symbols", SYMBOLS) or SYMBOLS

    for sym_key, sym_info in symbol_items.items():
        ticker = sym_info.get("ticker", f"{sym_key}=F")
        print(f"  Fetching {ticker} ({sym_info.get('name', sym_key)}) …", flush=True)
        df = fetch_data(ticker, days=days)
        if df.empty:
            continue

        # Reconcile multiplier from config vs hardcoded
        sym_info.setdefault("multiplier", SYMBOLS.get(sym_key, {}).get("multiplier", 0.25))

        for sd in search_dates:
            for sess_key, sess_info in SESSIONS.items():
                signals = analyze_orb(
                    sym_key, sym_info, df,
                    sess_key, sess_info, cfg_orb, sd
                )
                all_signals.extend(signals)

    # Sort by breakout time
    all_signals.sort(key=lambda s: s["breakout_time"])
    return all_signals


def format_report(signals: list[dict]) -> str:
    """Pretty-print ORB signals for Telegram / terminal."""
    if not signals:
        return (
            "📊 **ORB Scan Complete — No Signals Found**\n\n"
            "No opening range breakouts detected in the scanned period.\n"
            "The market may be quiet, or the data may be too delayed.\n\n"
            "*Run again closer to session opens for best results.*"
        )

    lines = [
        f"📊 **ORB Signals Found** ({len(signals)} signals)",
        f"_Scanned: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}_",
        "─" * 40,
    ]

    for s in signals:
        direction = "🟢 LONG" if s["direction"] == "LONG" else "🔴 SHORT"
        lines.append(
            f"\n**{s['symbol']}** ({s['name']}) — {s['session']}\n"
            f"{direction}\n"
            f"  Range: {s['range_low']} – {s['range_high']} "
            f"({s['range_size']} pts / {s['range_ticks']} ticks)\n"
            f"  Breakout: {s['breakout_price']} at "
            f"`{s['breakout_time'].strftime('%H:%M UTC')}`"
        )

    lines.append("\n" + "─" * 40)
    lines.append(
        "⚠️ _Educational analysis only. Uses delayed data._\n"
        "_Not financial advice. Verify with live data before trading._"
    )
    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    import argparse
    parser = argparse.ArgumentParser(description="ORB Futures Monitor")
    parser.add_argument("--date", type=str, default=None,
                        help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--days", type=int, default=5,
                        help="Days of history to scan (default: 5)")
    parser.add_argument("--config", type=str, default="config.yaml",
                        help="Path to config file")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of formatted text")
    args = parser.parse_args()

    print("\n🔍 ORB Monitor — Scanning futures data …\n", flush=True)
    signals = run(date_str=args.date, days=args.days, config_path=args.config)

    if args.json:
        import json
        print(json.dumps(signals, indent=2, default=str))
    else:
        report = format_report(signals)
        print(report)
        # Also save to log
        log_path = "orb_signals.log"
        with open(log_path, "a") as fh:
            fh.write(f"\n{'='*50}\n")
            fh.write(f"Scan: {datetime.now(UTC).isoformat()}\n")
            fh.write(report + "\n")

    print(f"\n✅ Done. {len(signals)} signals detected.\n", flush=True)


if __name__ == "__main__":
    main()
