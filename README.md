# 🤖 trading-bot V7 — Kripto Trading Botu

Binance Futures üzerinde otomatik alım-satım yapan, MiMo v2.5 AI ile grafik tabanlı sinyal doğrulaması yapan gelişmiş trading sistemi.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
![AI](https://img.shields.io/badge/AI-MiMo%20v2.5-FF6700?style=for-the-badge)
[![Binance](https://img.shields.io/badge/Binance-F0B90B?style=for-the-badge&logo=binance&logoColor=black)](https://www.binance.com/)

## ✨ Özellikler

| Modül | Açıklama | Durum |
|-------|----------|-------|
| 📊 **V7 Strategy** | Price Action + SMC Liquidity Sweep | ✅ |
| 🤖 **AI Verification** | MiMo v2.5 grafik doğrulama | ✅ |
| 🧠 **Adaptive Learning** | Günlük otomatik öğrenme | ✅ |
| 🎯 **Risk Management** | Drawdown, trailing stop | ✅ |
| 📱 **Telegram Bot** | Bildirimler ve komutlar | ✅ |
| 📊 **Backtest** | Geçmiş verilerle test | ✅ |

## 🚀 Hızlı Başlangıç

### Kurulum

```bash
# 1. Depoyu klonla
git clone https://github.com/yasar-afk/borsa-analiz-bot.git
cd borsa-analiz-bot

# 2. Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Konfigürasyon
cp .env.example .env
```

### .env Dosyası

```env
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
MIMO_API_KEY=your_mimo_api_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Çalıştırma

```bash
# Paper trading (varsayılan)
python live_v7.py

# Canlı borsa
python live_v7.py --live

# Tüm botları çalıştır
python run_all_bots.py
```

## 📊 Strateji (V7)

### Price Action — SMC Liquidity Sweep Reversal

```
100 mum swing high/low tarama
        ↓
EMA(180) trend filtresi
        ↓
ATR bazlı Stop-Loss (0.6x ATR)
        ↓
Dinamik RR (ADX >25 → 4.0, ADX 15-25 → 3.0)
        ↓
Multi-TF konfirmasyon (15m + 1h + 4h)
```

### Parametreler

| Parametre | Değer |
|-----------|-------|
| Sweep Window | 100 mum |
| Trend EMA | 180 periyot |
| ATR Çarpanı | 0.6x |
| Min SL | %2 |
| Max SL | %8 |
| Min Volatilite | %0.3 |
| Kaldıraç | 5x izole |

## 🤖 AI Entegrasyonu (MiMo v2.5)

### Giriş Doğrulama
```
Mum grafiği oluştur → RSI, ADX, EMA, Hacim hesapla
        ↓
MiMo'ya grafik + indikatörler gönder
        ↓
TRADE / SKIP karar
```

### Pozisyon İnceleme
- Her saat açık pozisyonlar MiMo tarafından incelenir
- HOLD / CLOSE / PARTIAL_CLOSE kararları
- %10 PnL: Otomatik CLOSE
- Boş reason: Otomatik CLOSE

### Hata Yönetimi
- **FAIL-CLOSE**: AI hata verince sinyal reddedilir
- **Reason validasyonu**: Boş/kısa reason otomatik SKIP/CLOSE

## 🛡️ Risk Yönetimi

| Parametre | Değer |
|-----------|-------|
| Max pozisyon | 10 |
| Pozisyon riski | %2 |
| Günlük drawdown | %5 |
| Kaldıraç | 5x izole |
| Komisyon | %0.063 |
| Cooldown | 24 saat |
| Arka arkaya kayıp | 2. → %50, 3. → %25 |
| Blacklist | 2+ kayıpta anında, 3+ kalıcı |

## 📱 Telegram Komutları

```
/durum    - Bot durumu
/status   - Açık pozisyonlar
/portfoy  - Portföy özeti
/pozisyon - Detaylı pozisyon bilgisi
/acik     - Açık pozisyon listesi
```

## 📁 Proje Yapısı

```
borsa-analiz-bot/
├── live_v7.py              # V7 ana bot
├── live_v5.py              # V5 bot
├── live_v65.py             # V6.5 Mean Reversion
├── run_all_bots.py         # Tümünü çalıştır
├── config_v7.yaml          # V7 ayarları
├── config.yaml             # Ana konfigürasyon
├── requirements.txt        # Bağımlılıklar
├── setup.py                # pip kurulum
│
├── src/                    # Kaynak kodları
│   ├── strategy/           # Strateji modülleri
│   │   ├── v7_pa_strategy.py
│   │   ├── ai_chart_verifier.py
│   │   ├── adaptive_learner.py
│   │   └── regime_detector.py
│   ├── risk/               # Risk yönetimi
│   ├── data/               # Veri çekme
│   └── utils/              # Yardımcı fonksiyonlar
│
├── data/                   # Fiyat verileri
├── logs/                   # İşlem logları
└── tests/                  # Test dosyaları
```

## 🔧 Konfigürasyon

```yaml
# config_v7.yaml
strategy:
  sweep_window: 100
  trend_ema: 180
  atr_multiplier: 0.6
  min_sl_pct: 0.02
  max_sl_pct: 0.08

risk:
  max_position_pct: 0.02
  max_daily_drawdown_pct: 0.05
  min_risk_reward_ratio: 3.0

execution:
  leverage: 5
  margin_mode: ISOLATED
```

## 🧪 Backtest

```bash
# V7 backtest
python backtest_v7.py

# Kapsamlı analiz
python analyze_v7_comprehensive.py
```

## 📊 Performans

| Metrik | Değer |
|--------|-------|
| Başlangıç | $10,000 |
| Güncel | $16,323 |
| Kâr | %+63.2 |
| Durum | Aktif (Paper Trading) |

## 🛠️ Teknoloji Stack

| Kategori | Teknoloji |
|----------|-----------|
| **Dil** | Python 3.10+ |
| **Borsa** | Binance Futures (ccxt) |
| **AI** | MiMo v2.5 (Xiaomi) |
| **ML** | Scikit-learn, HMM |
| **Bildirim** | Telegram Bot |
| **Veri** | Pandas, NumPy |
| **Grafik** | Matplotlib |

## ⚠️ Uyarı

Bu bot yatırım tavsiyesi değildir. Kripto para birimleri yüksek risk taşır. Paper trading ile test edin.

## 📝 Lisans

MIT License

---

**trading-bot V7** — MiMoCode tarafından geliştirildi 🚀
