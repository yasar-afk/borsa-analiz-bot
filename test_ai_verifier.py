"""
test_ai_verifier.py - MiMo v2.5 AI Grafik Dogrulayi Test Scripti
Calistir: python test_ai_verifier.py
"""
import os
import sys
import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("  XIAOMI MiMo v2.5 CHART VERIFIER - ENTEGRASYON TESTI")
print("=" * 60)

# -- 1. Kutuphane kontrolu ------------------------------------------------
print("\n[1/4] Kutuphane kontrolu...")
try:
    import openai
    print(f"  [OK] openai v{openai.__version__} yuklu")
except ImportError as e:
    print(f"  [HATA] openai YUKLENEMEDI: {e}")
    print("     -> pip install openai>=1.30.0")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use("Agg")
    print(f"  [OK] matplotlib v{matplotlib.__version__} yuklu")
except ImportError as e:
    print(f"  [HATA] matplotlib: {e}")
    sys.exit(1)

# -- 2. .env / API Key kontrolu -------------------------------------------
print("\n[2/4] API Anahtari ve Konfigurasyon kontrolu...")
api_key  = os.getenv("MIMO_API_KEY", "")
model    = os.getenv("MIMO_MODEL", "mimo-v2.5")
base_url = os.getenv("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1")

if not api_key or "<" in api_key or len(api_key) < 10:
    print("  [HATA] MIMO_API_KEY .env dosyasina yazilmamis!")
    sys.exit(1)

print(f"  [OK] MIMO_API_KEY: ...{api_key[-8:]}")
print(f"  [OK] Model      : {model}")
print(f"  [OK] Base URL   : {base_url}")

# -- 3. Modul import testi ------------------------------------------------
print("\n[3/4] AIChartVerifier modul testi...")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from src.strategy.ai_chart_verifier import AIChartVerifier
    verifier = AIChartVerifier()
    if verifier.is_enabled:
        print("  [OK] AIChartVerifier yuklendi ve AKTIF (MiMo v2.5)")
    else:
        print("  [UYARI] AIChartVerifier DEVRE DISI")
        sys.exit(1)
except Exception as e:
    print(f"  [HATA] AIChartVerifier yuklenemedi: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# -- 4. Gercek API cagrisi testi ------------------------------------------
print("\n[4/4] MiMo v2.5 API canli goruntu testi...")
print("      Sahte BTC/USDT mum grafigi olusturuluyor ve gonderiliyor...")

np.random.seed(42)
n = 80
close = 65000 + np.cumsum(np.random.randn(n) * 200)
high  = close + np.abs(np.random.randn(n) * 150)
low   = close - np.abs(np.random.randn(n) * 150)
open_ = close + np.random.randn(n) * 100

df_test = pd.DataFrame({
    "open":   open_,
    "high":   high,
    "low":    low,
    "close":  close,
    "volume": np.random.uniform(100, 1000, n),
}, index=pd.date_range("2026-06-01", periods=n, freq="1h"))

try:
    result = verifier.verify(
        symbol="BTC/USDT",
        direction="BUY",
        price=float(close[-1]),
        sl=float(close[-1] * 0.97),
        tp=float(close[-1] * 1.10),
        df=df_test,
        timeframe="1h",
    )

    print(f"\n  ---- YENI SINYAL SONUCU ----")
    print(f"  Karar     : {result.get('decision', '?')} | Onaylandi: {result.get('approved', '?')}")
    print(f"  Sebep     : {result.get('reason', '-')}")
    print(f"  Model     : {result.get('model', '-')}")
    print(f"  AI Bypass : {result.get('skipped_ai', False)}")

    print("\n[5/4] AIChartVerifier canli pozisyon inceleme testi...")
    review_result = verifier.review_position(
        symbol="BTC/USDT",
        direction="BUY",
        entry_price=float(close[-5]),
        current_price=float(close[-1]),
        sl=float(close[-5] * 0.95),
        tp=float(close[-5] * 1.15),
        df=df_test,
        opened_at=(pd.Timestamp.now() - pd.Timedelta(hours=14)).isoformat(),
        timeframe="1h",
    )
    print(f"\n  ---- ACIK POZISYON INCELEME SONUCU ----")
    print(f"  Eylem     : {review_result.get('action', '?')}")
    print(f"  Guven     : {review_result.get('confidence', '?')}")
    print(f"  Sebep     : {review_result.get('reason', '-')}")
    print(f"  Model     : {review_result.get('model', '-')}")
    print(f"  AI Bypass : {review_result.get('skipped_ai', False)}")

    print("\n" + "=" * 60)
    if result.get("skipped_ai") or review_result.get("skipped_ai"):
        print("  [BASARISIZ] API cagrisi yapilamadi - hatayi yukarida incele")
    else:
        print("  [BASARILI] MiMo v2.5 entegrasyonu ve pozisyon inceleme calisiyor!")
    print("=" * 60)

except Exception as e:
    print(f"\n  [HATA] {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)
