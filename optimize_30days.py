# -*- coding: utf-8 -*-
"""
optimize_30days.py — 30 gunluk veri uzerinde parametre optimizasyonu.
"""
import pandas as pd
import numpy as np
import os
import sys
import itertools
import random

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r"C:\Users\52tuz\Desktop\deneme borsa\data\historical_100d_15m_all"
INITIAL_CAPITAL = 10000.0
LEVERAGE = 5
COMMISSION_RATE = 0.00063
RISK_PER_TRADE = 0.02

# Test edilecek coinler (hizli test icin)
TEST_COINS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'AAVEUSDT']

def calculate_indicators(df):
    df = df.copy()
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(window=14).mean()
    loss = (-delta.clip(upper=0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift(1)).abs()
    low_close = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()
    return df

def run_backtest(df, params):
    df = calculate_indicators(df)
    df = df.sort_values('datetime').reset_index(drop=True)
    df_30d = df.tail(2880).reset_index(drop=True)

    ema_fast = params.get('ema_fast', 9)
    ema_slow = params.get('ema_slow', 21)
    rsi_buy_limit = params.get('rsi_buy_limit', 70)
    rsi_sell_limit = params.get('rsi_sell_limit', 30)
    atr_sl_mult = params.get('atr_sl_mult', 1.5)
    atr_tp_mult = params.get('atr_tp_mult', 3.0)
    min_sl_pct = params.get('min_sl_pct', 0.01)
    max_sl_pct = params.get('max_sl_pct', 0.08)

    df_30d['ema_fast'] = df_30d['close'].ewm(span=ema_fast, adjust=False).mean()
    df_30d['ema_slow'] = df_30d['close'].ewm(span=ema_slow, adjust=False).mean()

    capital = INITIAL_CAPITAL
    position = None
    trades = []
    equity = []

    closes = df_30d['close'].values
    highs = df_30d['high'].values
    lows = df_30d['low'].values
    ema_f = df_30d['ema_fast'].values
    ema_s = df_30d['ema_slow'].values
    rsi = df_30d['rsi'].values
    atr = df_30d['atr'].values

    for i in range(30, len(df_30d)):
        c = closes[i]
        e9 = ema_f[i]
        e21 = ema_s[i]
        prev_e9 = ema_f[i-1]
        prev_e21 = ema_s[i-1]
        r = rsi[i]
        a = atr[i]

        if pd.isna(e9) or pd.isna(e21) or pd.isna(a) or a == 0:
            equity.append(capital)
            continue

        if position is not None:
            hit_sl = False
            hit_tp = False
            if position['type'] == 'LONG':
                if lows[i] <= position['sl']: hit_sl = True
                elif highs[i] >= position['tp']: hit_tp = True
            else:
                if highs[i] >= position['sl']: hit_sl = True
                elif lows[i] <= position['tp']: hit_tp = True

            if hit_sl or hit_tp:
                exit_p = position['sl'] if hit_sl else position['tp']
                pnl_pct = (exit_p - position['entry']) / position['entry'] * 100 if position['type'] == 'LONG' else (position['entry'] - exit_p) / position['entry'] * 100
                pnl_usdt = position['size'] * pnl_pct / 100 * LEVERAGE
                commission = position['size'] * COMMISSION_RATE * 2
                capital += pnl_usdt - commission
                trades.append({'pnl': pnl_usdt - commission, 'result': 'WIN' if pnl_usdt > commission else 'LOSS'})
                position = None
                equity.append(capital)
                continue

        if position is None:
            if prev_e9 <= prev_e21 and e9 > e21 and r < rsi_buy_limit:
                sl = c - (a * atr_sl_mult)
                tp = c + (a * atr_tp_mult)
                risk = c - sl
                if risk > 0 and (tp - c) / risk >= 2.0:
                    sl_pct = risk / c
                    if min_sl_pct <= sl_pct <= max_sl_pct:
                        position = {'type': 'LONG', 'entry': c, 'sl': sl, 'tp': tp, 'size': capital * RISK_PER_TRADE / sl_pct}
            elif prev_e9 >= prev_e21 and e9 < e21 and r > rsi_sell_limit:
                sl = c + (a * atr_sl_mult)
                tp = c - (a * atr_tp_mult)
                risk = sl - c
                if risk > 0 and (c - tp) / risk >= 2.0:
                    sl_pct = risk / c
                    if min_sl_pct <= sl_pct <= max_sl_pct:
                        position = {'type': 'SHORT', 'entry': c, 'sl': sl, 'tp': tp, 'size': capital * RISK_PER_TRADE / sl_pct}

        equity.append(capital)

    return trades, capital

# Parametre grid
param_grid = {
    'ema_fast': [5, 9, 13],
    'ema_slow': [21, 30, 50],
    'rsi_buy_limit': [65, 70, 75],
    'rsi_sell_limit': [25, 30, 35],
    'atr_sl_mult': [1.0, 1.5, 2.0],
    'atr_tp_mult': [2.0, 3.0, 4.0],
    'min_sl_pct': [0.01, 0.02],
    'max_sl_pct': [0.06, 0.08],
}

# Rastgele orneklem
random.seed(42)
combos = list(itertools.product(*param_grid.values()))
sample = random.sample(combos, min(100, len(combos)))

results = []

for combo in sample:
    params = dict(zip(param_grid.keys(), combo))
    
    all_trades = []
    final_capitals = []
    
    for coin in TEST_COINS:
        file_path = os.path.join(DATA_DIR, f"{coin}_15m_100d.csv")
        if not os.path.exists(file_path):
            continue
        try:
            df = pd.read_csv(file_path)
            df['datetime'] = pd.to_datetime(df['datetime'])
            trades, final_cap = run_backtest(df, params)
            all_trades.extend(trades)
            final_capitals.append(final_cap)
        except:
            pass

    if not all_trades:
        continue

    wins = sum(1 for t in all_trades if t['result'] == 'WIN')
    total = len(all_trades)
    win_rate = wins / total * 100
    total_pnl = sum(t['pnl'] for t in all_trades)
    avg_capital = np.mean(final_capitals) if final_capitals else INITIAL_CAPITAL

    # Skor: win_rate * 2 + total_pnl / 100 - total * 0.1
    score = win_rate * 2 + total_pnl / 100 - total * 0.1

    results.append({
        'params': params,
        'trades': total,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_capital': avg_capital,
        'score': score,
    })

results.sort(key=lambda x: x['score'], reverse=True)

print("=== EN IYI 5 PARAMETRE ===\n")
for i, r in enumerate(results[:5]):
    print(f"#{i+1} Score: {r['score']:.2f}")
    print(f"   Trades: {r['trades']} | Win Rate: %{r['win_rate']:.0f}")
    print(f"   Total PnL: ${r['total_pnl']:+,.2f} | Avg Capital: ${r['avg_capital']:,.2f}")
    print(f"   Params: {r['params']}")
    print()
