# Sirius Trading - Pine Scripts

This directory contains custom algorithmic trading scripts designed for TradingView (Pine Script v5).

## Scripts

### 1. `SiriusAITrendMaster.pine`
A robust, trend-following strategy designed for crypto and equities. 

**Core Logic:**
- **Entry:** Uses a Fast/Slow EMA crossover.
- **Filter:** Validates momentum by requiring the price to be above/below the Volume Weighted Average Price (VWAP) before taking the cross.
- **Risk Management:** Implements an automated, dynamic ATR-based trailing stop-loss. It tightens the stop as the trade moves in your favor, locking in profits while giving the asset room to breathe based on current volatility.
