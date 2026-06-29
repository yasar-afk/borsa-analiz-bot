<div align="center">

# 🤖 Borsa Analiz Bot — V7

### Autonomous Crypto Trading with AI-Powered Chart Verification

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
![AI](https://img.shields.io/badge/AI-MiMo%20v2.5-FF6700?style=for-the-badge)
[![Binance](https://img.shields.io/badge/Binance-Futures-F0B90B?style=for-the-badge&logo=binance&logoColor=black)](https://www.binance.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 📊 V7 Strategy Engine
- **Price Action + SMC** Liquidity Sweep
- **Multi-timeframe** confirmation (15m, 1h, 4h)
- **Adaptive parameters** based on market regime
- **ATR-based** dynamic stop-loss

</td>
<td width="50%">

### 🤖 AI Verification
- **MiMo v2.5** chart analysis
- **Visual pattern** recognition
- **Risk assessment** before execution
- **Continuous learning** from outcomes

</td>
</tr>
<tr>
<td width="50%">

### 🛡️ Risk Management
- **Max 10** concurrent positions
- **2% risk** per trade
- **5% daily** drawdown limit
- **Trailing stop** protection

</td>
<td width="50%">

### 📱 Telegram Integration
- **Real-time** notifications
- **Portfolio** monitoring
- **Remote commands** for control
- **Trade alerts** with AI reasoning

</td>
</tr>
</table>

---

## 📈 Performance

<div align="center">

| Metric | Value |
|--------|-------|
| 🚀 Starting Capital | $10,000 |
| 💰 Current Value | $16,323 |
| 📈 Total Return | **+63.2%** |
| 📊 Status | Active (Paper Trading) |

</div>

---

## 🚀 Quick Start

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yasar-afk/borsa-analiz-bot.git
cd borsa-analiz-bot

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
```

### Environment Variables

```env
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
MIMO_API_KEY=your_mimo_api_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Run

```bash
# Paper trading (safe mode)
python live_v7.py

# Live trading (real money!)
python live_v7.py --live

# Run all bot versions
python run_all_bots.py
```

---

## 🧠 Strategy Overview

### V7: Price Action + SMC Liquidity Sweep

```
┌─────────────────────────────────────────────────────────────┐
│  100-candle swing high/low detection                        │
│         ↓                                                   │
│  EMA(180) trend filter                                      │
│         ↓                                                   │
│  ATR-based Stop-Loss (0.6x ATR)                            │
│         ↓                                                   │
│  Dynamic Risk:Reward (ADX >25 → 4.0, ADX 15-25 → 3.0)    │
│         ↓                                                   │
│  Multi-TF confirmation (15m + 1h + 4h)                     │
│         ↓                                                   │
│  🤖 MiMo AI Chart Verification                             │
│         ↓                                                   │
│  ✅ EXECUTE / ❌ SKIP                                       │
└─────────────────────────────────────────────────────────────┘
```

### Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `sweep_window` | 100 | Candles to scan for swing points |
| `trend_ema` | 180 | Trend filter period |
| `atr_multiplier` | 0.6 | Stop-loss ATR multiplier |
| `min_sl_pct` | 2% | Minimum stop-loss |
| `max_sl_pct` | 8% | Maximum stop-loss |
| `leverage` | 5x | Position leverage (isolated) |

---

## 🛡️ Risk Management

| Rule | Value | Action |
|------|-------|--------|
| Max Positions | 10 | Block new trades |
| Position Risk | 2% | Per-trade allocation |
| Daily Drawdown | 5% | Stop trading |
| Consecutive Losses | 2 → 50%, 3 → 25% | Reduce size |
| Blacklist | 2+ loss → immediate, 3+ → permanent | Block symbol |

---

## 📱 Telegram Commands

```
/durum    → Bot status & uptime
/status   → Open positions
/portfoy  → Portfolio summary
/pozisyon → Detailed position info
/acik     → List all open trades
```

---

## 📁 Project Structure

```
borsa-analiz-bot/
├── live_v7.py              # V7 main bot (Price Action + SMC)
├── live_v5.py              # V5 bot (Mean Reversion)
├── live_v65.py             # V6.5 hybrid strategy
├── run_all_bots.py         # Run all versions
│
├── config_v7.yaml          # V7 configuration
├── config.yaml             # Global configuration
├── requirements.txt        # Dependencies
├── setup.py                # Package setup
│
├── src/
│   ├── strategy/           # Trading strategies
│   │   ├── v7_pa_strategy.py      # Price Action engine
│   │   ├── ai_chart_verifier.py   # MiMo AI verification
│   │   ├── adaptive_learner.py    # Self-learning module
│   │   └── regime_detector.py     # Market regime detection
│   ├── risk/               # Risk management
│   │   └── engine.py              # Position sizing & limits
│   ├── data/               # Data fetching
│   └── utils/              # Utilities
│       ├── telegram_notifier.py   # Telegram alerts
│       ├── ai_analyzer.py         # AI analysis tools
│       └── chart_reader.py        # Chart visualization
│
├── backtest_v7.py          # Backtesting engine
├── analyze_v7_comprehensive.py  # Performance analysis
└── tests/                  # Test suite
```

---

## 🧪 Backtesting

```bash
# Run V7 backtest
python backtest_v7.py

# Comprehensive analysis
python analyze_v7_comprehensive.py

# Compare all strategies
python compare_3bots.py
```

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|--------------|
| **Language** | Python 3.10+ |
| **AI/ML** | MiMo v2.5, PyTorch, Scikit-learn, XGBoost, HMM |
| **Trading** | Binance Futures, ccxt |
| **Visualization** | Matplotlib, Plotly, mplfinance |
| **Notifications** | Telegram Bot API |
| **Data** | Pandas, NumPy, TA-Lib |
| **Optimization** | Optuna, SHAP |

---

## ⚠️ Disclaimer

> **This bot is NOT financial advice.** Cryptocurrency trading carries high risk. 
> Always test with paper trading first. Never invest more than you can afford to lose.

---

## 📝 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ by [Yaşar TÜZEN](https://github.com/yasar-afk)**

[![LinkedIn](https://img.shields.io/badge/Connect-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/yasar-afk)
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:yasar.tuzen.eng@gmail.com)

</div>
