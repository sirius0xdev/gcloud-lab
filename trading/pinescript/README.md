# Sirius Trading - Pine Scripts

This directory contains custom algorithmic trading scripts designed for TradingView (Pine Script v5).

## Scripts

### 1. `SiriusAITrendMaster.pine`
A robust, trend-following strategy designed for crypto and equities. 

**Core Logic:**
- **Entry:** Uses a Fast/Slow EMA crossover.
- **Filter:** Validates momentum by requiring the price to be above/below the Volume Weighted Average Price (VWAP) before taking the cross.
- **Risk Management:** Implements an automated, dynamic ATR-based trailing stop-loss.

### 2. `SiriusMeanReversion.pine`
A mean-reversion counter-trend strategy designed to catch over-extended moves in ranging markets.

**Core Logic:**
- **Entry:** Buys when the price crosses below the lower Bollinger Band and RSI is oversold (< 30). Shorts when price crosses above the upper Bollinger Band and RSI is overbought (> 70).
- **Risk Management:** Uses strict percentage-based Take Profit and Stop Loss limits set via the script inputs.
