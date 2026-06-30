# -*- coding: utf-8 -*-
"""
backtest_final.py — Optimize edilmis V7 ile 30 gunluk backtest.
"""
import pandas as pd
import numpy as np
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r"C:\Users\52tuz\Desktop\deneme borsa\data\historical_100d_15m_all"
INITIAL_CAPITAL = 10000.0
LEVERAGE = 5
COMMISSION_RATE = 0.00063
RISK_PER_TRADE = 0.02
COOLDOWN_HOURS = 24

COINS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT',
    'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT', 'MATICUSDT',
    'UNIUSDT', 'AAVEUSDT', 'NEARUSDT', 'FETUSDT', 'RENDERUSDT',
    'PEPEUSDT', 'SHIBUSDT', 'TRXUSDT', 'LTCUSDT', 'BCHUSDT'
]

# Optimize edilmis parametreler
PARAMS = {
    'ema_fast': 5,
    'ema_slow': 50,
    'rsi_buy_limit': 65,
    'rsi_sell_limit': 30,
    'atr_sl_mult': 1.5,
    'atr_tp_mult': 3.0,
    'min_sl_pct': 0.01,
    'max_sl_pct': 0.06,
}

def calculate_indicators(df):
    df = df.copy()
    df['ema_fast'] = df['close'].ewm(span=PARAMS['ema_fast'], adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=PARAMS['ema_slow'], adjust=False).mean()
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

def run_backtest_single(df, symbol):
    df = calculate_indicators(df)
    df = df.sort_values('datetime').reset_index(drop=True)
    df_30d = df.tail(2880).reset_index(drop=True)

    capital = INITIAL_CAPITAL
    position = None
    trades = []
    equity_curve = []
    last_trade_time = {}

    closes = df_30d['close'].values
    highs = df_30d['high'].values
    lows = df_30d['low'].values
    ema_f = df_30d['ema_fast'].values
    ema_s = df_30d['ema_slow'].values
    rsi = df_30d['rsi'].values
    atr = df_30d['atr'].values
    times = df_30d['datetime'].values

    for i in range(55, len(df_30d)):
        c = closes[i]
        e9 = ema_f[i]
        e21 = ema_s[i]
        prev_e9 = ema_f[i-1]
        prev_e21 = ema_s[i-1]
        r = rsi[i]
        a = atr[i]
        t = times[i]

        if pd.isna(e9) or pd.isna(e21) or pd.isna(a) or a == 0:
            equity_curve.append(capital)
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
                if position['type'] == 'LONG':
                    pnl_pct = (exit_p - position['entry']) / position['entry'] * 100
                else:
                    pnl_pct = (position['entry'] - exit_p) / position['entry'] * 100
                pnl_usdt = position['size'] * pnl_pct / 100 * LEVERAGE
                commission = position['size'] * COMMISSION_RATE * 2
                net_pnl = pnl_usdt - commission
                capital += net_pnl
                trades.append({
                    'symbol': symbol, 'type': position['type'],
                    'entry': position['entry'], 'exit': exit_p,
                    'pnl_pct': pnl_pct, 'pnl_usdt': net_pnl,
                    'result': 'WIN' if net_pnl > 0 else 'LOSS',
                    'entry_time': position['entry_time'], 'exit_time': t,
                })
                last_trade_time[symbol] = t
                position = None
                equity_curve.append(capital)
                continue

        if position is None:
            last_t = last_trade_time.get(symbol)
            if last_t is not None:
                try:
                    hours_diff = (pd.to_datetime(t) - pd.to_datetime(last_t)).total_seconds() / 3600
                    if hours_diff < COOLDOWN_HOURS:
                        equity_curve.append(capital)
                        continue
                except:
                    pass

            if prev_e9 <= prev_e21 and e9 > e21 and r < PARAMS['rsi_buy_limit']:
                sl = c - (a * PARAMS['atr_sl_mult'])
                tp = c + (a * PARAMS['atr_tp_mult'])
                risk = c - sl
                if risk > 0 and (tp - c) / risk >= 2.0:
                    sl_pct = risk / c
                    if PARAMS['min_sl_pct'] <= sl_pct <= PARAMS['max_sl_pct']:
                        position = {'type': 'LONG', 'entry': c, 'sl': sl, 'tp': tp,
                                    'size': capital * RISK_PER_TRADE / sl_pct, 'entry_time': t}

            elif prev_e9 >= prev_e21 and e9 < e21 and r > PARAMS['rsi_sell_limit']:
                sl = c + (a * PARAMS['atr_sl_mult'])
                tp = c - (a * PARAMS['atr_tp_mult'])
                risk = sl - c
                if risk > 0 and (c - tp) / risk >= 2.0:
                    sl_pct = risk / c
                    if PARAMS['min_sl_pct'] <= sl_pct <= PARAMS['max_sl_pct']:
                        position = {'type': 'SHORT', 'entry': c, 'sl': sl, 'tp': tp,
                                    'size': capital * RISK_PER_TRADE / sl_pct, 'entry_time': t}

        equity_curve.append(capital)

    return trades, equity_curve, capital

def main():
    print("=" * 60)
    print("V7 OPTIMIZE - 30 GUNLUK BACKTEST (FINAL)")
    print("=" * 60)
    print(f"Baslangic Sermayesi: ${INITIAL_CAPITAL:,.2f}")
    print(f"Kaldıraç: {LEVERAGE}x izole | Risk: %{RISK_PER_TRADE*100}")
    print(f"Parametreler: EMA {PARAMS['ema_fast']}/{PARAMS['ema_slow']} | RSI <{PARAMS['rsi_buy_limit']}/>{PARAMS['rsi_sell_limit']}")
    print()

    all_trades = []
    all_equity = []
    coin_results = {}

    for coin in COINS:
        file_path = os.path.join(DATA_DIR, f"{coin}_15m_100d.csv")
        if not os.path.exists(file_path):
            continue
        try:
            df = pd.read_csv(file_path)
            df['datetime'] = pd.to_datetime(df['datetime'])
            trades, equity, final_capital = run_backtest_single(df, coin)
            if trades:
                wins = sum(1 for t in trades if t['result'] == 'WIN')
                losses = sum(1 for t in trades if t['result'] == 'LOSS')
                total_pnl = sum(t['pnl_usdt'] for t in trades)
                win_rate = wins / len(trades) * 100
                coin_results[coin] = {'trades': len(trades), 'wins': wins, 'losses': losses,
                                      'win_rate': win_rate, 'pnl': total_pnl}
                all_trades.extend(trades)
                all_equity.extend(equity)
                print(f"{coin}: {len(trades)} islem | Win: %{win_rate:.0f} | K/Z: ${total_pnl:+,.2f}")
        except Exception as e:
            print(f"{coin}: HATA - {e}")

    print()
    print("=" * 60)
    print("GENEL SONUCLAR")
    print("=" * 60)

    total_trades = len(all_trades)
    total_wins = sum(1 for t in all_trades if t['result'] == 'WIN')
    total_losses = sum(1 for t in all_trades if t['result'] == 'LOSS')
    total_pnl = sum(t['pnl_usdt'] for t in all_trades)
    final_capital = INITIAL_CAPITAL + total_pnl
    win_rate = total_wins / total_trades * 100 if total_trades > 0 else 0
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

    peak = INITIAL_CAPITAL
    max_dd = 0
    for eq in all_equity:
        if eq > peak: peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd: max_dd = dd

    if all_trades:
        returns = [t['pnl_pct'] for t in all_trades]
        sharpe = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
    else:
        sharpe = 0

    print(f"Toplam Islem: {total_trades}")
    print(f"Kazanan: {total_wins} | Kaybeden: {total_losses}")
    print(f"Win Rate: %{win_rate:.1f}")
    print(f"Toplam K/Z: ${total_pnl:+,.2f}")
    print(f"Son Sermaye: ${final_capital:,.2f}")
    print(f"Getiri: %{(final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100:+.2f}")
    print(f"Max Drawdown: %{max_dd:.2f}")
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Ortalama K/Z/Islem: ${avg_pnl:+,.2f}")

    if all_trades:
        best = max(all_trades, key=lambda x: x['pnl_usdt'])
        worst = min(all_trades, key=lambda x: x['pnl_usdt'])
        print(f"\nEn Iyi: {best['symbol']} {best['type']} ${best['pnl_usdt']:+,.2f}")
        print(f"En Kotu: {worst['symbol']} {worst['type']} ${worst['pnl_usdt']:+,.2f}")

    print()
    print("=" * 60)
    print("COIN BAZINDA DETAY")
    print("=" * 60)
    print(f"{'Coin':<15} {'Islem':>7} {'Win%':>7} {'K/Z':>12}")
    print("-" * 45)
    for coin, r in sorted(coin_results.items(), key=lambda x: x[1]['pnl'], reverse=True):
        print(f"{coin:<15} {r['trades']:>7} %{r['win_rate']:>5.0f} ${r['pnl']:>+10,.2f}")

if __name__ == "__main__":
    main()
