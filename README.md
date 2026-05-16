# Elliot Wave Trading Bot

A high-performance, automated trading bot implementing the **Elliot Wave Method** for cryptocurrency markets. This bot is designed to identify trend exhaustion and execute high-probability reversals using a combination of structural analysis, momentum indicators, and Fibonacci retracements.

## 🚀 Key Features
- **Exchange Agnostic**: Built on `CCXT` to support major exchanges (Binance, Bybit, OKX, etc.).
- **Automated Wave Counting**: Heuristic-based detection of 5-wave impulse structures.
- **Advanced Momentum Analysis**: Integrated RSI and MACD divergence detection to confirm trend exhaustion between Wave 3 and Wave 5.
- **Smart Execution Engine**: Uses laddered limit orders to optimize entry prices and reduce slippage.
- **Risk Management**: Built-in Fibonacci-based targets and volatility-adjusted stop losses.
- **Dual Interface**:
  - **Terminal Dashboard**: A sleek, real-time TUI built with `rich`.
  - **Web Dashboard**: Modern HTML/JS interface for remote monitoring.
- **AI-Powered Support**: Includes a standalone AI Assistant for troubleshooting and strategy review.

## 🛠 Tech Stack
- **Engine**: Python 3.9+
- **Connectivity**: `CCXT` (Multi-exchange support)
- **Analytics**: `pandas-ta`
- **UI**: `Rich` (Terminal), Vanilla JS/CSS (Web)

## 🏁 Getting Started

### 1. Installation
```bash
git clone https://github.com/dxeroz2/elliot-wave-trading-bot.git
cd elliot-wave-trading-bot
pip install -r requirements.txt
```

### 2. Configuration
The bot uses environment variables for secure credential management. Set these before running:
```powershell
$env:EXCHANGE_API_KEY = "your_key"
$env:EXCHANGE_API_SECRET = "your_secret"
$env:EXCHANGE_PASSPHRASE = "your_passphrase"
```

### 3. Usage
- **Live Bot**: `python elliot_wave_bot.py`
- **Backtester**: `python elliot_wave_backtester.py`
- **AI Assistant**: `python elliot_ai_assistant.py`

## 📊 Strategy Logic
The bot follows a rigorous 5-step validation process:
1. **Macro Bias**: Validates trend direction using an EMA stack (8, 13, 21, 55, 200).
2. **Impulse Detection**: Scans for high-velocity price movements (>= 0.4% impulse).
3. **Structure Validation**: Verifies the Elliot Wave count using swing high/low pivot points.
4. **Momentum Confirmation**: Checks for RSI Divergence and MACD Histogram momentum loss.
5. **Execution**: Deploys a laddered order strategy with isolated margin.

---
*Disclaimer: Trading cryptocurrencies involves significant risk. This bot is for research and educational purposes only. Past performance does not guarantee future results.*
