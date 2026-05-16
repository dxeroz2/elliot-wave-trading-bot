# Elliot Wave Bot Protocol 📜

This file defines the operational protocol for the Elliot Wave Trading Bot and its AI Assistant.

## 1. Bot Architecture
- **Core Bot**: `elliot_wave_bot.py` (Real-time execution on binance/CCXT)
- **Backtester**: `elliot_wave_backtester.py` (Historical simulation)
- **AI Assistant**: `elliot_ai_assistant.py` (Troubleshooting and review)
- **UI Dashboard**: `index.html` (Web-based monitoring)

## 2. Strategy Rules (Elliot Wave Method)
1. **Macro Bias**: Check higher timeframe (15m/1h) EMAs (8, 13, 21, 55, 200).
2. **Impulse Detection**: Identify volatility impulses >= 0.4%.
3. **Wave Validation**: Heuristic check for 5-wave Elliott structure using swing pivots.
4. **Divergence**: Confirm momentum loss via RSI Divergence between Wave 3 and Wave 5.
5. **Execution**: Execute laddered limit orders based on Fibonacci retracement levels (38.2% TP, 61.8% secondary entry).

## 3. Security
- **API Keys**: Use environment variables (`EXCHANGE_API_KEY`, `EXCHANGE_API_SECRET`).
- **Safety**: Stop-loss is mandatory for all trades (default 1.5%).

---
*Note: This is an open-source project for educational purposes.*
