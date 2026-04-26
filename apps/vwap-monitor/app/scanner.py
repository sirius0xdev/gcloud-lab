#!/usr/bin/env python3
"""
VWAP Wave Breach Scanner
========================
Continuous monitoring daemon. Scans instruments on a schedule,
detects VWAP wave breaches, and pushes alerts via Telegram.

Environment variables:
  TELEGRAM_BOT_TOKEN    — Telegram Bot API token (required)
  TELEGRAM_CHAT_ID      — Chat ID to send alerts to (required)
  SCAN_INTERVAL_SEC     — Seconds between scans (default: 120)
  BREACH_THRESHOLD      — Sigma threshold for alerts (default: 2.0)

No LLM overhead — pure Python, ~20MB RAM.
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone

import requests
import yfinance as yf
import pandas as pd
from apscheduler.schedulers.background import BlockingScheduler

# ── Config ──────────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]
SCAN_INTERVAL_SEC   = int(os.environ.get("SCAN_INTERVAL_SEC", "120"))
BREACH_THRESHOLD    = float(os.environ.get("BREACH_THRESHOLD", "2.0"))

INSTRUMENTS = {
    "Gold Futures":  {"ticker": "GC=F",  "decimal": 2},
    "NASDAQ":        {"ticker": "^IXIC", "decimal": 2},
    "S&P 500":       {"ticker": "^GSPC", "decimal": 2},
    "Crude Oil":     {"ticker": "CL=F",  "decimal": 2},
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-5s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Track last alert state to prevent spam (no repeat within same threshold direction)
_last_alert = {}


# ── Telegram ────────────────────────────────────────────────────────────────

def send_telegram(message: str) -> bool:
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":     TELEGRAM_CHAT_ID,
        "text":        message,
        "parse_mode":  "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        log.info("Telegram alert sent: %s", message[:80])
        return True
    except Exception as e:
        log.error("Telegram send failed: %s", e)
        return False


# ── VWAP Calculation ────────────────────────────────────────────────────────

def compute_vwap(data: pd.DataFrame) -> dict | None:
    """Compute cumulative VWAP, σ, and deviation."""
    df = data.copy()
    df["typical"] = (df["High"] + df["Low"] + df["Close"]) / 3.0
    df["tp_vol"]  = df["typical"] * df["Volume"]

    cum_tp_vol = df["tp_vol"].cumsum()
    cum_vol    = df["Volume"].cumsum().replace(0, 1)

    df["cum_vwap"]  = cum_tp_vol / cum_vol
    df["deviation"] = df["typical"] - df["cum_vwap"]
    df["cum_var"]   = (df["deviation"] ** 2).cumsum() / cum_vol
    df["sigma"]     = df["cum_var"] ** 0.5

    last = df.iloc[-1]
    if last["sigma"] <= 0:
        return None

    return {
        "price":      last["Close"],
        "vwap":       last["cum_vwap"],
        "sigma":      last["sigma"],
        "dev_sigmas": (last["Close"] - last["cum_vwap"]) / last["sigma"],
    }


def fetch_data(ticker: str) -> pd.DataFrame:
    """Fetch recent intraday data via yfinance."""
    try:
        data = yf.Ticker(ticker).history(period="1d", interval="1m", auto_adjust=True)
    except Exception:
        data = pd.DataFrame()

    if len(data) < 30:
        data = yf.Ticker(ticker).history(period="5d", interval="1m", auto_adjust=True)
        cutoff = pd.Timestamp.now(tz=data.index.tz) - pd.Timedelta(hours=24)
        data = data[data.index >= cutoff]

    return data


# ── Scanner ─────────────────────────────────────────────────────────────────

def run_scan() -> None:
    """Execute a full scan cycle and push any breaches."""
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    log.info("── Scan %s ──", ts)

    breaches = []

    for name, cfg in INSTRUMENTS.items():
        try:
            data = fetch_data(cfg["ticker"])
            if data.empty or len(data) < 20:
                log.warning("SKIP %s — insufficient data (%d bars)", name, len(data))
                continue

            info = compute_vwap(data)
            if info is None:
                log.warning("SKIP %s — zero sigma", name)
                continue

            d = cfg["decimal"]
            dev = info["dev_sigmas"]
            log.info("  %-14s $%10.2f | VWAP $%10.2f | %+.2fσ", name, info["price"], info["vwap"], dev)

            if abs(dev) >= BREACH_THRESHOLD:
                # Prevent repeat spam: only alert if state changed
                alert_key = f"{name}:{dev > 0}"
                if _last_alert.get(alert_key) == "breach":
                    log.info("  → %s already in breach, skipping repeat", name)
                    continue

                breaches.append((name, cfg["decimal"], dev, info["price"], info["vwap"], info["sigma"]))
                _last_alert[alert_key] = "breach"
            else:
                _last_alert[f"{name}:True"]  = "clean"
                _last_alert[f"{name}:False"] = "clean"

        except Exception as e:
            log.error("ERROR %s: %s", name, e)

    # Push alerts
    for name, d, dev, price, vwap, sigma in breaches:
        direction = "⬆️ UP" if dev > 0 else "⬇️ DOWN"
        band_label = f"±{int(abs(dev))}σ"
        severity = "🚨 **EXTREME**" if abs(dev) >= 3.0 else "⚡ **BREACH**"

        msg = (
            f"{severity} — VWAP Wave Alert\n\n"
            f"**{name}** broke through **{band_label}** band\n"
            f"Deviation: **{dev:+.2f}σ**\n"
            f"Price: **${price:.{d}f}** | VWAP: **${vwap:.{d}f}**\n"
            f"σ: ${sigma:.{d}f} | {direction}\n\n"
            f"_at {ts}_"
        )
        send_telegram(msg)


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("=" * 60)
    log.info("  VWAP Wave Breach Scanner")
    log.info("  Interval: %d sec | Threshold: ±%.1fσ", SCAN_INTERVAL_SEC, BREACH_THRESHOLD)
    log.info("  Telegram: @chat_id=%s", TELEGRAM_CHAT_ID)
    log.info("=" * 60)

    # Validate Telegram connectivity
    send_telegram(
        "🟢 *VWAP Breach Scanner* is online.\n"
        f"Scanning every **{SCAN_INTERVAL_SEC}s** — threshold ±**{BREACH_THRESHOLD:.1f}σ**\n"
        f"Monitoring: Gold, NASDAQ, S&P 500, Crude Oil"
    )

    scheduler = BlockingScheduler()
    scheduler.add_job(run_scan, "interval", seconds=SCAN_INTERVAL_SEC, id="scan")
    # Run immediately on start
    run_scan()

    log.info("Scanner running. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
