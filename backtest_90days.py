# -*- coding: utf-8 -*-
"""
backtest_90days.py — 90 gunluk backtest (Filtresiz vs Filtreli)
Coin kalite filtresi ile karsilastirmali test.
"""
import pandas as pd
import numpy as np
import os
import sys
import copy

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

PARAMS = {
    'ema_fast': 5, 'ema_slow': 50,
    'rsi_buy_limit': 65, 'rsi_sell_limit': 30,
    'atr_sl_mult': 1.5, 'atr_tp_mult': 3.0,
    'min_sl_pct': 0.01, 'max_sl_pct': 0.06,
}


class CoinQualityFilter:
    def __init__(self, min_trades=3, min_win_rate=0.30):
        self.coin_stats = {}
        self.min_trades = min_trades
        self.min_win_rate = min_win_rate

    def update_stats(self, symbol, win_rate, avg_pnl, total_trades):
        self.coin_stats[symbol] = {'win_rate': win_rate, 'avg_pnl': avg_pnl, 'trades': total_trades}

    def should_trade(self, symbol):
        stats = self.coin_stats.get(symbol)
        if stats is None: return True
        if stats['trades'] < self.min_trades: return True
        if stats['win_rate'] < self.min_win_rate: return False
        return True

    def get_size_mult(self, symbol):
        stats = self.coin_stats.get(symbol)
        if stats is None or stats['trades'] < self.min_trades: return 1.0
        wr = stats['win_rate']
        if wr >= 0.50: return 1.5
        elif wr >= 0.40: return 1.25
        elif wr >= 0.30: return 1.0
        elif wr >= 0.20: return 0.5
        else: return 0.0


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


def run_backtest(df, use_filter=False, quality_filter=None, update_interval=2880):
    """
    90 gunluk backtest calistir.
    update_interval: Her kac mumda bir kalite filtresini guncelle (2880 = 30 gun)
    """
    df = calculate_indicators(df)
    df = df.sort_values('datetime').reset_index(drop=True)
    df_90d = df.tail(6720).reset_index(drop=True)  # 90 gun = 6720 mum (15dk)

    capital = INITIAL_CAPITAL
    position = None
    trades = []
    equity_curve = []
    last_trade_time = {}
    symbol = df_90d.get('symbol', ['UNKNOWN'])[0] if 'symbol' in df_90d.columns else 'UNKNOWN'

    closes = df_90d['close'].values
    highs = df_90d['high'].values
    lows = df_90d['low'].values
    ema_f = df_90d['ema_fast'].values
    ema_s = df_90d['ema_slow'].values
    rsi_arr = df_90d['rsi'].values
    atr_arr = df_90d['atr'].values
    times = df_90d['datetime'].values

    for i in range(55, len(df_90d)):
        c = closes[i]
        e_f = ema_f[i]
        e_s = ema_s[i]
        prev_e_f = ema_f[i-1]
        prev_e_s = ema_s[i-1]
        r = rsi_arr[i]
        a = atr_arr[i]
        t = times[i]

        if pd.isna(e_f) or pd.isna(e_s) or pd.isna(a) or a == 0:
            equity_curve.append(capital)
            continue

        # Kalite filtresi guncelleme
        if use_filter and quality_filter and i > 0 and i % update_interval == 0 and len(trades) > 0:
            wins = sum(1 for tr in trades if tr['result'] == 'WIN')
            wr = wins / len(trades)
            avg_pnl = np.mean([tr['pnl_usdt'] for tr in trades])
            quality_filter.update_stats(symbol, wr, avg_pnl, len(trades))

        # Mevcut pozisyon kontrolu
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

        # Yeni pozisyon ac
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

            # Kalite filtresi kontrolu
            if use_filter and quality_filter and not quality_filter.should_trade(symbol):
                equity_curve.append(capital)
                continue

            # Pozisyon buyuklugu carpani
            size_mult = 1.0
            if use_filter and quality_filter:
                size_mult = quality_filter.get_size_mult(symbol)

            if size_mult <= 0:
                equity_curve.append(capital)
                continue

            # BUY
            if prev_e_f <= prev_e_s and e_f > e_s and r < PARAMS['rsi_buy_limit']:
                sl = c - (a * PARAMS['atr_sl_mult'])
                tp = c + (a * PARAMS['atr_tp_mult'])
                risk = c - sl
                if risk > 0 and (tp - c) / risk >= 2.0:
                    sl_pct = risk / c
                    if PARAMS['min_sl_pct'] <= sl_pct <= PARAMS['max_sl_pct']:
                        position_size = capital * RISK_PER_TRADE / sl_pct * size_mult
                        position = {'type': 'LONG', 'entry': c, 'sl': sl, 'tp': tp,
                                    'size': position_size, 'entry_time': t}

            # SELL
            elif prev_e_f >= prev_e_s and e_f < e_s and r > PARAMS['rsi_sell_limit']:
                sl = c + (a * PARAMS['atr_sl_mult'])
                tp = c - (a * PARAMS['atr_tp_mult'])
                risk = sl - c
                if risk > 0 and (c - tp) / risk >= 2.0:
                    sl_pct = risk / c
                    if PARAMS['min_sl_pct'] <= sl_pct <= PARAMS['max_sl_pct']:
                        position_size = capital * RISK_PER_TRADE / sl_pct * size_mult
                        position = {'type': 'SHORT', 'entry': c, 'sl': sl, 'tp': tp,
                                    'size': position_size, 'entry_time': t}

        equity_curve.append(capital)

    return trades, equity_curve, capital


def run_full_backtest(use_filter=False):
    """Tum coinler uzerinde 90 gunluk backtest."""
    quality_filter = CoinQualityFilter() if use_filter else None
    all_trades = []
    all_equity = []
    coin_results = {}
    coin_data = {}

    # Once tum verileri yukle
    for coin in COINS:
        file_path = os.path.join(DATA_DIR, f"{coin}_15m_100d.csv")
        if not os.path.exists(file_path):
            continue
        try:
            df = pd.read_csv(file_path)
            df['datetime'] = pd.to_datetime(df['datetime'])
            coin_data[coin] = df
        except:
            pass

    # Filtreli mod icin: ilk 30 gunu calistirarak baslangic istatistiklerini olustur
    if use_filter and quality_filter:
        print("  Kalite filtresi baslangic istatistikleri olusturuluyor...")
        for coin, df in coin_data.items():
            trades, _, _ = run_backtest(df, use_filter=False)
            if len(trades) >= 3:
                wins = sum(1 for t in trades if t['result'] == 'WIN')
                wr = wins / len(trades)
                avg_pnl = np.mean([t['pnl_usdt'] for t in trades])
                quality_filter.update_stats(coin, wr, avg_pnl, len(trades))

    # Simdi 90 gunluk backtest calistir
    for coin, df in coin_data.items():
        try:
            trades, equity, final_capital = run_backtest(
                df, use_filter=use_filter, quality_filter=quality_filter
            )
            if trades:
                wins = sum(1 for t in trades if t['result'] == 'WIN')
                losses = sum(1 for t in trades if t['result'] == 'LOSS')
                total_pnl = sum(t['pnl_usdt'] for t in trades)
                win_rate = wins / len(trades) * 100
                coin_results[coin] = {
                    'trades': len(trades), 'wins': wins, 'losses': losses,
                    'win_rate': win_rate, 'pnl': total_pnl
                }
                all_trades.extend(trades)
                all_equity.extend(equity)
        except Exception as e:
            pass

    return all_trades, all_equity, coin_results


def print_results(label, all_trades, all_equity, coin_results):
    """Sonuclari yazdir."""
    print()
    print("=" * 60)
    print(f"  {label}")
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

    print(f"Toplam Islem: {total_trades}")
    print(f"Kazanan: {total_wins} | Kaybeden: {total_losses}")
    print(f"Win Rate: %{win_rate:.1f}")
    print(f"Toplam K/Z: ${total_pnl:+,.2f}")
    print(f"Son Sermaye: ${final_capital:,.2f}")
    print(f"Getiri: %{(final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100:+.2f}")
    print(f"Max Drawdown: %{max_dd:.2f}")
    print(f"Ortalama K/Z/Islem: ${avg_pnl:+,.2f}")

    if coin_results:
        print()
        print(f"{'Coin':<15} {'Islem':>7} {'Win%':>7} {'K/Z':>12}")
        print("-" * 45)
        for coin, r in sorted(coin_results.items(), key=lambda x: x[1]['pnl'], reverse=True):
            print(f"{coin:<15} {r['trades']:>7} %{r['win_rate']:>5.0f} ${r['pnl']:>+10,.2f}")

    return {
        'trades': total_trades, 'wins': total_wins, 'losses': total_losses,
        'win_rate': win_rate, 'pnl': total_pnl, 'final_capital': final_capital,
        'max_dd': max_dd, 'avg_pnl': avg_pnl,
    }


def main():
    print("=" * 60)
    print("  90 GUNLUK BACKTEST — FILTRESIZ vs FILTRELI")
    print("=" * 60)
    print(f"Baslangic Sermayesi: ${INITIAL_CAPITAL:,.2f}")
    print(f"Kaldıraç: {LEVERAGE}x izole | Risk: %{RISK_PER_TRADE*100}")
    print()

    # Filtresiz test
    print("Filtresiz test calistiriliyor...")
    trades_no, equity_no, results_no = run_full_backtest(use_filter=False)
    stats_no = print_results("FILITRESIZ 90 GUN", trades_no, equity_no, results_no)

    # Filtreli test
    print("\nFiltreli test calistiriliyor...")
    trades_fi, equity_fi, results_fi = run_full_backtest(use_filter=True)
    stats_fi = print_results("FILTRELI 90 GUN", trades_fi, equity_fi, results_fi)

    # Karsilastirma
    print()
    print("=" * 60)
    print("  KARSILASTIRMA")
    print("=" * 60)
    print(f"{'Metrik':<25} {'Filtresiz':>15} {'Filtreli':>15} {'Fark':>12}")
    print("-" * 70)
    print(f"{'Islem Sayisi':<25} {stats_no['trades']:>15} {stats_fi['trades']:>15} {stats_fi['trades']-stats_no['trades']:>+12}")
    print(f"{'Win Rate':<25} %{stats_no['win_rate']:>13.1f} %{stats_fi['win_rate']:>13.1f} %{stats_fi['win_rate']-stats_no['win_rate']:>+10.1f}")
    print(f"{'Toplam K/Z':<25} ${stats_no['pnl']:>+13,.2f} ${stats_fi['pnl']:>+13,.2f} ${stats_fi['pnl']-stats_no['pnl']:>+10,.2f}")
    print(f"{'Getiri':<25} %{(stats_no['final_capital']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:>+13.2f}% {(stats_fi['final_capital']-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:>+13.2f}% {(stats_fi['final_capital']-stats_no['final_capital'])/INITIAL_CAPITAL*100:>+10.2f}%")
    print(f"{'Max Drawdown':<25} %{stats_no['max_dd']:>13.2f} %{stats_fi['max_dd']:>13.2f} %{stats_fi['max_dd']-stats_no['max_dd']:>+10.2f}")


if __name__ == "__main__":
    main()
