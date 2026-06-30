# -*- coding: utf-8 -*-
"""
src/strategy/v7_pa_strategy.py — V7 Optimize Trend Takip Stratejisi
30 gunluk backtest ile optimize edilmis: EMA 5/50, RSI 65/30.
"""
import pandas as pd
import numpy as np


class V7PriceActionStrategy:
    """
    Trading Bot V7 — Optimize Trend Takip Stratejisi
    
    EMA Cross (5/50) + RSI + ATR tabanli stop-loss/take-profit
    30 gunluk backtest ile optimize edilmis parametreler
    """

    def __init__(
        self,
        ema_fast: int = 5,
        ema_slow: int = 50,
        rsi_buy_limit: float = 65,
        rsi_sell_limit: float = 30,
        atr_sl_mult: float = 1.5,
        atr_tp_mult: float = 3.0,
        min_sl_pct: float = 0.01,
        max_sl_pct: float = 0.06,
        # Eski parametreler (uyumluluk icin)
        sweep_window: int = 50,
        max_hold_sweep: int = 3,
        target_rr: float = 2.0,
        trend_ema: int = 100,
        atr_multiplier: float = 0.6,
        use_volume_filter: bool = True,
        volume_threshold: float = 0.15,
        min_volatility_pct: float = 0.2,
        use_premium_discount: bool = False,
        max_tp_pct: float = 0.30,
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_buy_limit = rsi_buy_limit
        self.rsi_sell_limit = rsi_sell_limit
        self.atr_sl_mult = atr_sl_mult
        self.atr_tp_mult = atr_tp_mult
        self.min_sl_pct = min_sl_pct
        self.max_sl_pct = max_sl_pct
        # Eski parametreler
        self.sweep_window = sweep_window
        self.max_hold_sweep = max_hold_sweep
        self.target_rr = target_rr
        self.trend_ema = trend_ema
        self.atr_multiplier = atr_multiplier
        self.use_volume_filter = use_volume_filter
        self.volume_threshold = volume_threshold
        self.min_volatility_pct = min_volatility_pct
        self.use_premium_discount = use_premium_discount
        self.max_tp_pct = max_tp_pct

    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """V7 sinyallerini hesaplar — Optimize Trend Takip."""
        df = df.copy()

        # EMA'lar
        df['ema_fast'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()

        # RSI
        delta = df['close'].diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # ATR
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()

        # Sinyal kolonlari
        df['signal'] = 'HOLD'
        df['entry_price'] = 0.0
        df['sl_price'] = 0.0
        df['tp_price'] = 0.0

        start_idx = 55
        if start_idx >= len(df):
            return df

        closes = df['close'].values
        ema_f = df['ema_fast'].values
        ema_s = df['ema_slow'].values
        rsi = df['rsi'].values
        atr = df['atr'].values

        signals = ['HOLD'] * len(df)
        entry_prices = [0.0] * len(df)
        sl_prices = [0.0] * len(df)
        tp_prices = [0.0] * len(df)

        for i in range(start_idx, len(df)):
            c = closes[i]
            e_f = ema_f[i]
            e_s = ema_s[i]
            prev_e_f = ema_f[i-1]
            prev_e_s = ema_s[i-1]
            r = rsi[i]
            a = atr[i]

            if pd.isna(e_f) or pd.isna(e_s) or pd.isna(a) or a == 0:
                continue

            # BUY: EMA_fast > EMA_slow cross + RSI < limit
            if prev_e_f <= prev_e_s and e_f > e_s and r < self.rsi_buy_limit:
                sl = c - (a * self.atr_sl_mult)
                tp = c + (a * self.atr_tp_mult)
                risk = c - sl
                if risk > 0 and (tp - c) / risk >= 2.0:
                    sl_pct = risk / c
                    if self.min_sl_pct <= sl_pct <= self.max_sl_pct:
                        signals[i] = 'BUY'
                        entry_prices[i] = c
                        sl_prices[i] = sl
                        tp_prices[i] = tp

            # SELL: EMA_fast < EMA_slow cross + RSI > limit
            elif prev_e_f >= prev_e_s and e_f < e_s and r > self.rsi_sell_limit:
                sl = c + (a * self.atr_sl_mult)
                tp = c - (a * self.atr_tp_mult)
                risk = sl - c
                if risk > 0 and (c - tp) / risk >= 2.0:
                    sl_pct = risk / c
                    if self.min_sl_pct <= sl_pct <= self.max_sl_pct:
                        signals[i] = 'SELL'
                        entry_prices[i] = c
                        sl_prices[i] = sl
                        tp_prices[i] = tp

        df['signal'] = signals
        df['entry_price'] = entry_prices
        df['sl_price'] = sl_prices
        df['tp_price'] = tp_prices

        return df
