# -*- coding: utf-8 -*-
"""
diagnose_signals.py - Botlarin neden sinyal uretmedigini analiz eder.
"""
import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np

from src.data.historical import HistoricalDataFetcher
from src.strategy.v7_pa_strategy import V7PriceActionStrategy
from src.strategy.v5_pa_strategy import V5PriceActionStrategy
from src.strategy.smc_utils import get_premium_discount_zone


def check_premium_discount_bias(symbols, fetcher):
    discount_count = 0
    premium_count = 0
    eq_count = 0

    for sym in symbols:
        try:
            df = fetcher.fetch_ohlcv(sym, "1h", limit=200)
            if df.empty or len(df) < 100:
                continue
            df["swing_high"] = df["high"].shift(1).rolling(window=100).max()
            df["swing_low"]  = df["low"].shift(1).rolling(window=100).min()
            close = df["close"].iloc[-1]
            sh    = df["swing_high"].iloc[-1]
            sl    = df["swing_low"].iloc[-1]
            zone  = get_premium_discount_zone(close, sh, sl)
            if zone == "DISCOUNT":
                discount_count += 1
            elif zone == "PREMIUM":
                premium_count += 1
            else:
                eq_count += 1
        except Exception:
            pass

    total = discount_count + premium_count + eq_count
    print("\n" + "=" * 60)
    print("PREMIUM/DISCOUNT ZONE ANALIZI")
    print("=" * 60)
    print(f"  DISCOUNT (BUY icin uygun) : {discount_count} ({discount_count/max(total,1)*100:.0f}%)")
    print(f"  PREMIUM  (SELL icin uygun): {premium_count} ({premium_count/max(total,1)*100:.0f}%)")
    print(f"  EQUILIBRIUM               : {eq_count}")
    print("=" * 60)


def check_strategy(symbols, fetcher, strategy, version="V7"):
    EXCLUDED = {"PAXG/USDT", "RLUSD/USDT", "FDUSD/USDT", "USDC/USDT"}

    total_signals = 0
    no_data = 0
    low_vol  = 0
    no_sweep = 0
    errors   = 0

    print("\n" + "=" * 60)
    print(f"{version} STRATEJI TESHISI - {len(symbols)} Sembol")
    print("=" * 60)

    for sym in symbols:
        if sym in EXCLUDED:
            continue

        for tf in ["15m", "1h", "4h"]:
            try:
                df = fetcher.fetch_ohlcv(sym, tf, limit=500)
                if df.empty or len(df) < 200:
                    no_data += 1
                    if tf == "1h":
                        print(f"  NO_DATA : {sym} [{tf}] - {len(df)} mum")
                    continue

                # V7 icin volatilite filtresi
                if version == "V7":
                    vol = df["close"].pct_change(20).abs().iloc[-1] * 100
                    if pd.isna(vol) or vol < 0.3:
                        low_vol += 1
                        if tf == "1h":
                            print(f"  LOW_VOL : {sym} [{tf}] - vol={vol:.3f}%")
                        continue

                df_sig = strategy.calculate_signals(df)

                # Son 5 mum
                last5 = df_sig.tail(5)
                found = last5[last5["signal"].isin(["BUY", "SELL"])]

                if not found.empty:
                    for _, row in found.iterrows():
                        total_signals += 1
                        print(f"  SIGNAL  : {sym} [{tf}] {row['signal']} @ {row['entry_price']:.8g} | SL:{row['sl_price']:.8g} | TP:{row['tp_price']:.8g}")
                else:
                    no_sweep += 1
                    if tf == "1h":
                        # Debug: EMA ve zone durumu
                        ema   = df_sig["trend_ema_val"].iloc[-1]
                        close = df_sig["close"].iloc[-1]
                        sh    = df_sig["swing_high"].iloc[-1]
                        sl_   = df_sig["swing_low"].iloc[-1]
                        zone  = get_premium_discount_zone(close, sh, sl_) if not (pd.isna(sh) or pd.isna(sl_)) else "N/A"
                        ema_ok = "ABOVE_EMA" if close > ema else "BELOW_EMA"
                        
                        # Son 100 mumda herhangi sinyal var mi?
                        any100 = df_sig.tail(100)
                        cnt100 = len(any100[any100["signal"].isin(["BUY","SELL"])])

                        print(f"  NO_SIG  : {sym} [{tf}] | {ema_ok} | Zone:{zone} | Son100mum_sinyal:{cnt100}")

            except Exception as e:
                errors += 1
                print(f"  ERROR   : {sym} [{tf}] - {e}")

    print("\n" + "=" * 60)
    print(f"{version} OZET:")
    print(f"  Sinyal bulundu   : {total_signals}")
    print(f"  Yetersiz veri    : {no_data}")
    print(f"  Dusuk volatilite : {low_vol}")
    print(f"  Sweep/MSS yok    : {no_sweep}")
    print(f"  Hata             : {errors}")
    print("=" * 60 + "\n")


def main():
    TOP_N = 30
    fetcher = HistoricalDataFetcher()

    print(f"Top {TOP_N} sembol cekiliyor...")
    symbols = fetcher.fetch_top_symbols(top_n=TOP_N, quote="USDT")
    print(f"{len(symbols)} sembol alindi.")

    # 1. Zone bias analizi
    check_premium_discount_bias(symbols, fetcher)

    # 2. V7 strateji testi
    v7 = V7PriceActionStrategy()
    check_strategy(symbols, fetcher, v7, version="V7")

    # 3. V5 strateji testi
    v5 = V5PriceActionStrategy()
    check_strategy(symbols, fetcher, v5, version="V5")


if __name__ == "__main__":
    main()
