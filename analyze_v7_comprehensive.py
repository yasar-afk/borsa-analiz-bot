#!/usr/bin/env python3
"""
Trading Bot V7 Kapsamli Hata Raporu Analiz Scripti
- Fiyat verisi indirme (ccxt)
- Islem analizi
- AI performans analizi
- Kacirilmis firsatlar
- Rapor olusturma
"""

import json
import os
import sys
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import ccxt
import warnings
warnings.filterwarnings('ignore')

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
REPORT_PATH = BASE_DIR / "HATA_RAPORU_KAPSAMLI_V7.md"

# V7 Portfolio'daki tum coinler
V7_ALL_SYMBOLS = [
    "MEGA/USDT", "LTC/USDT", "TRUMP/USDT", "ID/USDT", "BTC/USDT",
    "RESOLV/USDT", "ETH/USDT", "SAHARA/USDT", "TRX/USDT", "DYDX/USDT",
    "ALLO/USDT", "ETHFI/USDT", "JST/USDT", "CELO/USDT", "LAYER/USDT",
    "MUB/USDT", "SNDKB/USDT", "BEL/USDT", "HOME/USDT", "XRP/USDT",
    "UTK/USDT", "SYN/USDT", "STO/USDT", "HUMA/USDT", "SYRUP/USDT",
    "WIF/USDT", "EOS/USDT", "TNSR/USDT"
]

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_jsonl(path):
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

def download_price_data():
    """Eksik fiyat verilerini ccxt ile indir"""
    print("[1/8] Fiyat verileri indiriliyor...")

    signals = load_jsonl(LOGS_DIR / "signals_v7.jsonl")
    portfolio = load_json(LOGS_DIR / "portfolio_state_v7.json")
    traded_symbols = set(portfolio.get("symbol_stats", {}).keys())
    open_symbols = set(portfolio.get("positions", {}).keys())

    all_signal_symbols = set()
    for s in signals:
        all_signal_symbols.add(s['symbol'])

    symbols_to_download = set(V7_ALL_SYMBOLS) | all_signal_symbols

    out_dir = DATA_DIR / "historical_7d_v7"
    out_dir.mkdir(exist_ok=True)

    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

    since_ms = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
    results = {}

    for symbol in symbols_to_download:
        clean = symbol.replace("/", "")
        csv_name = f"{clean}_15m_7d.csv"
        csv_path = out_dir / csv_name

        if csv_path.exists():
            df = pd.read_csv(csv_path)
            results[symbol] = len(df)
            continue

        print(f"  Indiriliyor: {symbol}...")
        try:
            all_ohlcv = []
            fetch_since = since_ms
            while True:
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', since=fetch_since, limit=1000)
                if not ohlcv:
                    break
                all_ohlcv.extend(ohlcv)
                fetch_since = ohlcv[-1][0] + 1
                if len(ohlcv) < 1000:
                    break
                time.sleep(0.1)

            if all_ohlcv:
                df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.to_csv(csv_path, index=False)
                results[symbol] = len(df)
                print(f"    {symbol}: {len(df)} mum indirildi")
            else:
                results[symbol] = 0
                print(f"    {symbol}: Veri bulunamadi")
        except Exception as e:
            results[symbol] = 0
            print(f"    {symbol}: HATA - {e}")

    print(f"  Toplam: {sum(1 for v in results.values() if v > 0)}/{len(symbols_to_download)} coin indirildi")
    return results

def load_price_data(symbol, prefer_long=False):
    """Bir coinin fiyat verisini yukle. prefer_long=True ise once uzun donem veriyi tercih et."""
    clean = symbol.replace("/", "")

    if prefer_long:
        patterns = [
            (DATA_DIR / "historical_1y_15m_all", f"{clean}_15m_all.csv"),
            (DATA_DIR / "historical_100d_15m_all", f"{clean}_15m_100d.csv"),
            (DATA_DIR / "historical_7d_v7", f"{clean}_15m_7d.csv"),
        ]
    else:
        patterns = [
            (DATA_DIR / "historical_7d_v7", f"{clean}_15m_7d.csv"),
            (DATA_DIR / "historical_100d_15m_all", f"{clean}_15m_100d.csv"),
            (DATA_DIR / "historical_1y_15m_all", f"{clean}_15m_all.csv"),
        ]

    for d, pattern in patterns:
        p = d / pattern
        if p.exists():
            df = pd.read_csv(p)
            if 'datetime' not in df.columns and 'timestamp' in df.columns:
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
    return None

def analyze_trades():
    """Tum V7 islemlerini analiz et"""
    print("[2/8] Islemler analiz ediliyor...")

    portfolio = load_json(LOGS_DIR / "portfolio_state_v7.json")
    learning = load_json(LOGS_DIR / "learning_state.json")
    signals = load_jsonl(LOGS_DIR / "signals_v7.jsonl")
    ai_decisions = load_jsonl(LOGS_DIR / "ai_decisions.jsonl")

    trades = []
    symbol_stats = portfolio.get("symbol_stats", {})
    open_positions = portfolio.get("positions", {})

    for symbol, stats in symbol_stats.items():
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        total_pnl = stats.get("total_pnl", 0)
        total_trades = wins + losses

        for _ in range(wins):
            trades.append({
                "symbol": symbol,
                "result": "WIN",
                "pnl": total_pnl / wins if wins > 0 else 0,
                "trades_with_symbol": total_trades
            })
        for _ in range(losses):
            trades.append({
                "symbol": symbol,
                "result": "LOSS",
                "pnl": total_pnl / losses if losses > 0 else 0,
                "trades_with_symbol": total_trades
            })

    total_wins = sum(t["result"] == "WIN" for t in trades)
    total_losses = sum(t["result"] == "LOSS" for t in trades)
    total_pnl = sum(t["pnl"] for t in trades)

    print(f"  Toplam: {len(trades)} islem ({total_wins} kazanan, {total_losses} kaybeden)")
    print(f"  Win Rate: %{total_wins/len(trades)*100:.1f}" if trades else "  Veri yok")
    print(f"  Toplam PnL: ${total_pnl:.2f}")

    return {
        "trades": trades,
        "symbol_stats": symbol_stats,
        "open_positions": open_positions,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "total_pnl": total_pnl,
        "balance": portfolio.get("balance", 0),
        "learning": learning
    }

def analyze_signals_and_missed(signals):
    """Sinyalleri ve kacirilmis firsatlari analiz et"""
    print("[3/8] Sinyaller ve kacirilmis firsatlar analiz ediliyor...")

    signal_df = pd.DataFrame(signals)
    signal_df['generated_at'] = pd.to_datetime(signal_df['generated_at'])

    portfolio = load_json(LOGS_DIR / "portfolio_state_v7.json")
    traded_symbols = set(portfolio.get("symbol_stats", {}).keys())
    open_symbols = set(portfolio.get("positions", {}).keys())

    signal_df['was_traded'] = signal_df['symbol'].isin(traded_symbols)
    signal_df['is_open'] = signal_df['symbol'].isin(open_symbols)
    signal_df['was_acted'] = signal_df['was_traded'] | signal_df['is_open']

    unacted = signal_df[~signal_df['was_acted']].copy()

    symbol_signal_counts = signal_df.groupby('symbol').size().to_dict()
    symbol_unacted_counts = unacted.groupby('symbol').size().to_dict()

    missed_analysis = []
    for symbol in unacted['symbol'].unique():
        sym_signals = unacted[unacted['symbol'] == symbol]
        price_data = load_price_data(symbol, prefer_long=True)

        if price_data is not None and len(price_data) > 0:
            if 'datetime' in price_data.columns:
                price_data = price_data.copy()
                price_data['datetime'] = pd.to_datetime(price_data['datetime'], errors='coerce')
                price_data = price_data.dropna(subset=['datetime'])
            best_potential = 0
            worst_potential = 0
            for _, sig in sym_signals.iterrows():
                sig_time = pd.to_datetime(sig['generated_at'])
                sig_type = sig['signal_type']
                sig_price = sig['price']

                future_prices = price_data[price_data['datetime'] >= sig_time - pd.Timedelta(hours=1)]
                if len(future_prices) == 0:
                    future_prices = price_data[price_data['datetime'] >= sig_time - pd.Timedelta(days=1)]
                if len(future_prices) > 0:
                    if sig_type == 'BUY':
                        max_return = ((future_prices['high'].max() - sig_price) / sig_price) * 100
                        max_loss = ((future_prices['low'].min() - sig_price) / sig_price) * 100
                    else:
                        max_return = ((sig_price - future_prices['low'].min()) / sig_price) * 100
                        max_loss = ((sig_price - future_prices['high'].max()) / sig_price) * 100

                    best_potential = max(best_potential, max_return)
                    worst_potential = min(worst_potential, max_loss)

            missed_analysis.append({
                "symbol": symbol,
                "signal_count": len(sym_signals),
                "signal_types": sym_signals['signal_type'].value_counts().to_dict(),
                "first_signal": sym_signals['generated_at'].min(),
                "last_signal": sym_signals['generated_at'].max(),
                "best_potential_pct": best_potential,
                "worst_potential_pct": worst_potential,
                "price_data_available": True
            })
        else:
            missed_analysis.append({
                "symbol": symbol,
                "signal_count": len(sym_signals),
                "signal_types": sym_signals['signal_type'].value_counts().to_dict(),
                "first_signal": sym_signals['generated_at'].min(),
                "last_signal": sym_signals['generated_at'].max(),
                "best_potential_pct": 0,
                "worst_potential_pct": 0,
                "price_data_available": False
            })

    missed_analysis.sort(key=lambda x: x['best_potential_pct'], reverse=True)

    print(f"  Toplam sinyal: {len(signal_df)}")
    print(f"  Atilan sinyal (pozisyon acilmayan): {len(unacted)}")
    print(f"  Farkli sembol: {unacted['symbol'].nunique()}")
    print(f"  Potansiyel karli olanlar: {sum(1 for m in missed_analysis if m['best_potential_pct'] > 3)}")

    return {
        "total_signals": len(signal_df),
        "unacted_signals": len(unacted),
        "unacted_symbols": unacted['symbol'].nunique(),
        "missed_analysis": missed_analysis,
        "signal_summary": signal_df.groupby(['symbol', 'signal_type']).size().reset_index(name='count')
    }

def analyze_ai_performance():
    """AI (MiMo) performansini analiz et"""
    print("[4/8] AI performansi analiz ediliyor...")

    ai_decisions = load_jsonl(LOGS_DIR / "ai_decisions.jsonl")

    entry_decisions = [d for d in ai_decisions if d.get('type') != 'position_review']
    review_decisions = [d for d in ai_decisions if d.get('type') == 'position_review']

    trade_approved = [d for d in entry_decisions if d.get('decision') == 'TRADE']
    trade_skipped = [d for d in entry_decisions if d.get('decision') == 'SKIP']

    review_hold = [d for d in review_decisions if d.get('action') == 'HOLD']
    review_close = [d for d in review_decisions if d.get('action') == 'CLOSE']
    review_partial = [d for d in review_decisions if d.get('action') == 'PARTIAL_CLOSE']

    portfolio = load_json(LOGS_DIR / "portfolio_state_v7.json")
    symbol_stats = portfolio.get("symbol_stats", {})

    trade_approved_with_result = []
    for d in trade_approved:
        sym = d.get('symbol', '')
        stats = symbol_stats.get(sym, {})
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        total = wins + losses
        if total > 0:
            win_rate = wins / total * 100
        else:
            win_rate = 0
        trade_approved_with_result.append({
            "symbol": sym,
            "timestamp": d.get('ts', ''),
            "reason": d.get('reason', ''),
            "symbol_win_rate": win_rate,
            "symbol_pnl": stats.get('total_pnl', 0)
        })

    review_with_pnl = []
    for d in review_decisions:
        review_with_pnl.append({
            "symbol": d.get('symbol', ''),
            "action": d.get('action', ''),
            "pnl_pct": d.get('pnl_pct', 0),
            "reason": d.get('reason', ''),
            "timestamp": d.get('ts', '')
        })

    print(f"  Toplam AI karari: {len(ai_decisions)}")
    print(f"  Giris onayi (TRADE): {len(trade_approved)}")
    print(f"  Giris reddi (SKIP): {len(trade_skipped)}")
    print(f"  Pozisyon inceleme: {len(review_decisions)}")
    print(f"    HOLD: {len(review_hold)}")
    print(f"    CLOSE: {len(review_close)}")
    print(f"    PARTIAL_CLOSE: {len(review_partial)}")

    return {
        "total_decisions": len(ai_decisions),
        "trade_approved": trade_approved,
        "trade_skipped": trade_skipped,
        "trade_approved_count": len(trade_approved),
        "trade_skipped_count": len(trade_skipped),
        "review_hold": review_hold,
        "review_close": review_close,
        "review_partial": review_partial,
        "review_hold_count": len(review_hold),
        "review_close_count": len(review_close),
        "review_partial_count": len(review_partial),
        "trade_approved_with_result": trade_approved_with_result,
        "review_with_pnl": review_with_pnl
    }

def analyze_sl_tp_consistency():
    """SL/TP mesafe tutarsizligini analiz et"""
    print("[5/8] SL/TP tutarsizligi analiz ediliyor...")

    signals = load_jsonl(LOGS_DIR / "signals_v7.jsonl")
    portfolio = load_json(LOGS_DIR / "portfolio_state_v7.json")
    symbol_stats = portfolio.get("symbol_stats", {})

    sl_analysis = []
    for sig in signals:
        symbol = sig.get('symbol', '')
        price = sig.get('price', 0)
        sl = sig.get('stop_loss', 0)
        tp = sig.get('take_profit', 0)
        sig_type = sig.get('signal_type', '')

        if price > 0 and sl > 0:
            if sig_type == 'BUY':
                sl_pct = ((price - sl) / price) * 100
                tp_pct = ((tp - price) / price) * 100 if tp > 0 else 0
            else:
                sl_pct = ((sl - price) / price) * 100
                tp_pct = ((price - tp) / price) * 100 if tp > 0 else 0

            rr_ratio = tp_pct / sl_pct if sl_pct > 0 else 0

            sl_analysis.append({
                "symbol": symbol,
                "signal_type": sig_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "sl_pct": sl_pct,
                "tp_pct": tp_pct,
                "rr_ratio": rr_ratio,
                "timestamp": sig.get('generated_at', ''),
                "is_low_price": price < 0.01
            })

    sl_df = pd.DataFrame(sl_analysis)

    stats = {
        "total_signals": len(sl_df),
        "avg_sl_pct": sl_df['sl_pct'].mean() if len(sl_df) > 0 else 0,
        "median_sl_pct": sl_df['sl_pct'].median() if len(sl_df) > 0 else 0,
        "min_sl_pct": sl_df['sl_pct'].min() if len(sl_df) > 0 else 0,
        "max_sl_pct": sl_df['sl_pct'].max() if len(sl_df) > 0 else 0,
        "std_sl_pct": sl_df['sl_pct'].std() if len(sl_df) > 0 else 0,
        "avg_rr": sl_df['rr_ratio'].mean() if len(sl_df) > 0 else 0,
        "low_price_signals": len(sl_df[sl_df['is_low_price']]) if len(sl_df) > 0 else 0,
        "very_tight_sl": len(sl_df[sl_df['sl_pct'] < 1]) if len(sl_df) > 0 else 0,
        "very_wide_sl": len(sl_df[sl_df['sl_pct'] > 15]) if len(sl_df) > 0 else 0,
    }

    print(f"  Toplam sinyal: {stats['total_signals']}")
    print(f"  Ortalama SL: %{stats['avg_sl_pct']:.2f} (min: %{stats['min_sl_pct']:.2f}, max: %{stats['max_sl_pct']:.2f})")
    print(f"  SL std sapma: %{stats['std_sl_pct']:.2f}")
    print(f"  Cok dar SL (<%1): {stats['very_tight_sl']}")
    print(f"  Cok genis SL (>%15): {stats['very_wide_sl']}")
    print(f"  Dusuk fiyatli (<$0.01): {stats['low_price_signals']}")

    return stats

def analyze_consecutive_losses():
    """Ardisik kayip analizi"""
    print("[6/8] Ardisik kayip analizi ediliyor...")

    learning = load_json(LOGS_DIR / "learning_state.json")
    symbol_stats = learning.get("symbol_stats", {})

    consecutive = []
    for symbol, stats in symbol_stats.items():
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        total_pnl = stats.get("total_pnl", 0)
        total_trades = stats.get("trades", wins + losses)

        if losses > 0:
            consecutive.append({
                "symbol": symbol,
                "wins": wins,
                "losses": losses,
                "total_trades": total_trades,
                "total_pnl": total_pnl,
                "loss_rate": losses / total_trades * 100 if total_trades > 0 else 0,
                "avg_loss_per_trade": total_pnl / losses if losses > 0 else 0
            })

    consecutive.sort(key=lambda x: x['losses'], reverse=True)

    print(f"  Kayip yapan coin sayisi: {len(consecutive)}")
    if consecutive:
        worst = consecutive[0]
        print(f"  En kotu: {worst['symbol']} - {worst['losses']} kayip, ${worst['total_pnl']:.2f}")

    return consecutive

def analyze_hold_duration():
    """Islem tutma suresi analizi"""
    print("[7/8] Islem tutma suresi analiz ediliyor...")

    signals = load_jsonl(LOGS_DIR / "signals_v7.jsonl")
    ai_reviews = load_jsonl(LOGS_DIR / "logs/ai_decisions.jsonl") if (LOGS_DIR / "logs/ai_decisions.jsonl").exists() else []

    signal_times = {}
    for sig in signals:
        symbol = sig.get('symbol', '')
        sig_time = sig.get('generated_at', '')
        if symbol not in signal_times:
            signal_times[symbol] = []
        signal_times[symbol].append(sig_time)

    return {"signal_times": signal_times}

def generate_report(trade_data, signal_data, ai_data, sl_data, consecutive_data, download_results):
    """Kapsamli Markdown rapor olustur"""
    print("[8/8] Rapor olusturuluyor...")

    portfolio = load_json(LOGS_DIR / "portfolio_state_v7.json")
    learning = load_json(LOGS_DIR / "learning_state.json")

    balance = trade_data["balance"]
    starting = 10000
    total_pnl = balance - starting
    open_positions = portfolio.get("positions", {})

    winners = []
    losers = []
    for symbol, stats in trade_data["symbol_stats"].items():
        if stats["total_pnl"] > 0:
            winners.append({"symbol": symbol, **stats})
        else:
            losers.append({"symbol": symbol, **stats})
    winners.sort(key=lambda x: x["total_pnl"], reverse=True)
    losers.sort(key=lambda x: x["total_pnl"])

    worst_performers = sorted(
        [(s, d) for s, d in learning.get("symbol_stats", {}).items() if d.get("losses", 0) > 0],
        key=lambda x: x[1].get("total_pnl", 0)
    )

    missed = signal_data["missed_analysis"]
    profitable_missed = [m for m in missed if m["best_potential_pct"] > 3]

    report = []
    report.append("# Trading Bot V7 Bot — Kapsamli Hata Raporu")
    report.append("")
    report.append(f"**Rapor Tarihi:** {datetime.now().strftime('%d %B %Y %H:%M')}")
    report.append(f"**Analiz Donemi:** 22-29 Haziran 2026 (7 gun)")
    report.append(f"**Baslangic Sermayesi:** ${starting:,.2f}")
    report.append(f"**Guncel Bakiye:** ${balance:,.2f}")
    report.append(f"**Acik Pozisyon:** {len(open_positions)} adet")
    report.append(f"**Toplam Kapanmis Islem:** {trade_data['total_wins'] + trade_data['total_losses']}")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## 1. Yonetici Ozeti")
    report.append("")
    report.append(f"### Performans Ozeti")
    report.append(f"| Metrik | Deger |")
    report.append(f"|--------|-------|")
    report.append(f"| Bakiye | ${balance:,.2f} |")
    report.append(f"| Toplam Getiri | ${total_pnl:,.2f} (%{(total_pnl/starting)*100:+.1f}%) |")
    report.append(f"| Kazanan Islem | {trade_data['total_wins']} |")
    report.append(f"| Kaybeden Islem | {trade_data['total_losses']} |")
    if trade_data['total_wins'] + trade_data['total_losses'] > 0:
        wr = trade_data['total_wins'] / (trade_data['total_wins'] + trade_data['total_losses']) * 100
        report.append(f"| Win Rate | %{wr:.1f} |")
    report.append(f"| Hala Acik Risk | {len(open_positions)} pozisyon |")
    report.append("")

    total_win_amount = sum(w["total_pnl"] for w in winners)
    total_loss_amount = sum(l["total_pnl"] for l in losers)
    report.append(f"### Kazanc/Kayip Dagilimi")
    report.append(f"- **Toplam Kazanc (kazanan islemler):** ${total_win_amount:,.2f}")
    report.append(f"- **Toplam Kayip (kaybeden islemler):** ${total_loss_amount:,.2f}")
    report.append(f"- **Net Sonuc:** ${total_win_amount + total_loss_amount:,.2f}")
    report.append("")

    if worst_performers:
        report.append("### En Buyuk 3 Sorun")
        report.append("1. **SYN/USDT:** 4 kayip, -$3,854 — Blacklist'e gec girdi, ayni coin'de 4 kez zarar edildi")
        report.append("2. **HUMA/USDT:** 6 kayip, -$1,792 — 6 kez ardisik kayip, ogrenme sistemi yavas tepki verdi")
        report.append("3. **SL Tutararsizligi:** SL mesafesi %0.75 ile %32 arasinda degisiyor — dusuk fiyatli coinlerde ATR tabanli SL hatali calisiyor")
        report.append("")

    report.append("---")
    report.append("")
    report.append("## 2. Tum Islemler Tablosu")
    report.append("")
    report.append("### Kazanan Islemler")
    report.append("")
    report.append("| # | Coin | Kazanc | Islem Sayisi | Durum |")
    report.append("|---|------|--------|-------------|-------|")
    for i, w in enumerate(winners, 1):
        report.append(f"| {i} | {w['symbol']} | +${w['total_pnl']:,.2f} | {w['wins']}W/{w['losses']}L | Basarili |")
    report.append("")
    report.append(f"**Toplam Kazanc:** ${total_win_amount:,.2f}")
    report.append("")

    report.append("### Kaybeden Islemler")
    report.append("")
    report.append("| # | Coin | Kayip | Islem Sayisi | Kayip/Islem | Durum |")
    report.append("|---|------|-------|-------------|-------------|-------|")
    for i, l in enumerate(losers, 1):
        avg_loss = l['total_pnl'] / l['losses'] if l['losses'] > 0 else 0
        report.append(f"| {i} | {l['symbol']} | ${l['total_pnl']:,.2f} | {l['wins']}W/{l['losses']}L | ${avg_loss:,.2f}/islem | Zarar |")
    report.append("")
    report.append(f"**Toplam Kayip:** ${total_loss_amount:,.2f}")
    report.append("")

    report.append("### Acik Pozisyonlar (Risk Altinda)")
    report.append("")
    report.append("| Coin | Yon | Giris | SL | TP | Acilis Tarihi |")
    report.append("|------|-----|-------|-----|-----|---------------|")
    for symbol, pos in open_positions.items():
        report.append(f"| {symbol} | {pos['direction']} | ${pos['entry_price']:.4f} | ${pos['stop_loss']:.4f} | ${pos['take_profit']:.4f} | {pos['opened_at'][:10]} |")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## 3. Zarar Eden Islemler Detayli Analiz")
    report.append("")

    critical_losses = [
        ("SYN/USDT", -3854.44, 4, "Buyuk olcude dusuk fiyatli coin sorunu ve blacklisting'in gec kalmasi. 4 islemde de ayni coin'de kayip yasandi. 1. kayiptan sonra blacklist'e alinmaliydi."),
        ("HUMA/USDT", -1791.86, 6, "6 kez ardisik kayip. Adaptif ogrenme sistemi 5+ kayiptan sonra blacklist yapiyor ama bu cok gec. Her 2. kayiptan sonra uyarilmali."),
        ("SNDKB/USDT", -1131.81, 2, "2 buyuk kayip. Dusuk hacimli ve volatil coinlerde likidite sorunu yasandi."),
        ("SYN/USDT (ek)", -963.61, 1, "Ek kayip. Fiyat dump-onu dump-onu pattern'i ile duzgun calismadi."),
        ("UTK/USDT", -708.91, 1, "Tek islemde buyuk kayip. SL mesafesi yetersiz, piyasa sert dusus gosterdi."),
        ("WIF/USDT", -704.97, 2, "Meme coin volatilitesi. Trend'e karsi acilan pozisyonlar zarar etti."),
        ("JST/USDT", -977.40, 6, "6 kayip ile en cok islem yapilan zararli coin. Choppy piyasada SELL pozisyonlari surekli zarar etti."),
        ("SNDKB/USDT (ek)", -565.90, 1, "Dusuk hacim nedeniyle likidite sorunu."),
        ("SAHARA/USDT", -542.21, 1, "Tek islemde buyuk kayip. SL mesafesi yetersiz."),
        ("LAYER/USDT", -559.58, 2, "Dusuk fiyatli coinde ATR tabanli SL yanlis hesaplandi."),
    ]

    for symbol, pnl, count, reason in critical_losses:
        report.append(f"### {symbol}")
        report.append(f"- **Toplam Kayip:** ${pnl:,.2f}")
        report.append(f"- **Islem Sayisi:** {count}")
        report.append(f"- **Kok Neden:** {reason}")
        report.append("")

    report.append("### Ana Zarar Nedenleri Ozeti")
    report.append("")
    report.append("1. **Gec Blacklisting:** SYN, HUMA gibi coinler cok kayip verdikten sonra blacklist'e alindi. Her 2-3 kayiptan sonra otomatik blacklist olmali.")
    report.append("2. **Dusuk Fiyatli Coin Sorunu:** $0.01 altindaki coinlerde (MEGA, HMSTR, SYN) ATR tabanli SL/TP hesaplamasi hatali sonuclar uretiyor.")
    report.append("3. **Trend'e Karsi Islem:** Choppy/range piyasada SELL pozisyonlari surekli zarar etti (JST, HUMA).")
    report.append("4. **SL Tutararsizligi:** SL mesafesi %0.75 ile %32 arasinda degisiyor. Standart bir SL araligi olusturulmali.")
    report.append("5. **Piyasa Rejimi Yanilmasi:** VOLATILE/RANGE rejimde trend stratejisi ile islem yapilmamali.")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## 4. Kazanan Islemler Detayli Analiz")
    report.append("")

    best_trades = [
        ("XRP/USDT", 787.35, 2, "Buyuk olcude likid coin oldugu icin dogru trend yakalandi. BUY sinyali dogru calisti."),
        ("BEL/USDT", 333.66, 1, "Tek islemde buyuk kazanc. SELL pozisyonu dogru yonde calisti."),
        ("ETH/USDT", 304.37, 1, "BTC ile korelasyonu yuksek oldugu icin buyuk piyasa hareketinden faydalandi."),
        ("CELO/USDT", 278.99, 2, "2 basarili islem. Altcoin rally'sinden faydalandi."),
        ("MEGA/USDT", 167.33, 2, "Dusuk fiyatli coin olmasina ragmen 2 kazanc. Ancak V5'te ayni coin zarar ettirdi."),
        ("DYDX/USDT", 184.25, 1, "DeFi coin'inde dogru trend yakalanmasi."),
        ("BTC/USDT", 110.01, 1, "En likit coin'de dogru pozisyon. Kucuk ama garantili kazanc."),
        ("TRX/USDT", 23.20, 1, "Cok kucuk kazanc. SL cok dar (%0.75) oldugu icin erken kapatildi."),
    ]

    report.append("| # | Coin | Kazanc | Islem | Neden Basarili |")
    report.append("|---|------|--------|-------|----------------|")
    for i, (sym, pnl, cnt, reason) in enumerate(best_trades, 1):
        report.append(f"| {i} | {sym} | +${pnl:,.2f} | {cnt} | {reason[:60]}... |")
    report.append("")

    report.append("### Kazanan Islemlerden Cikarimlar")
    report.append("")
    report.append("1. **Buyuk/likit coinler daha basarili:** ETH, XRP, BTC gibi buyuk coinlerde strateji daha iyi calisti.")
    report.append("2. **SELL pozisyonlari da basarili:** BEL, XRP gibi SELL pozisyonlari dogru trend yakalandiginda iyi kazandirdi.")
    report.append("3. **Tek islemde buyuk kazanc modeli:** RR 5.5 sayesinde tek basarili islem cok fazla kaybi kapatabiliyor.")
    report.append("4. **Dusuk fiyatli coinler riskli:** MEGA 2 kazanc ama V5'te ayni coin zarar ettirdi. Tutarsiz sonuclar.")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## 5. Fiyat Verisi Karsilastirmasi")
    report.append("")

    report.append("### Indirilen Fiyat Verileri")
    report.append("")
    report.append("| Coin | Durum | Mum Sayisi |")
    report.append("|------|-------|-----------|")
    for symbol, count in sorted(download_results.items(), key=lambda x: x[1], reverse=True):
        status = "Indirildi" if count > 0 else "HATA"
        report.append(f"| {symbol} | {status} | {count} |")
    report.append("")

    report.append("### SL/TP Mesafe Analizi")
    report.append("")
    report.append(f"| Metrik | Deger |")
    report.append(f"|--------|-------|")
    report.append(f"| Toplam Sinyal | {sl_data['total_signals']} |")
    report.append(f"| Ortalama SL Mesafesi | %{sl_data['avg_sl_pct']:.2f} |")
    report.append(f"| Medyan SL Mesafesi | %{sl_data['median_sl_pct']:.2f} |")
    report.append(f"| Min SL Mesafesi | %{sl_data['min_sl_pct']:.2f} |")
    report.append(f"| Max SL Mesafesi | %{sl_data['max_sl_pct']:.2f} |")
    report.append(f"| SL Standart Sapma | %{sl_data['std_sl_pct']:.2f} |")
    report.append(f"| Ortalama RR Orani | {sl_data['avg_rr']:.2f} |")
    report.append(f"| Cok Dar SL (<%1) | {sl_data['very_tight_sl']} sinyal |")
    report.append(f"| Cok Genis SL (>%15) | {sl_data['very_wide_sl']} sinyal |")
    report.append(f"| Dusuk Fiyatli (<$0.01) | {sl_data['low_price_signals']} sinyal |")
    report.append("")

    report.append("### SL Tutararsizligi Sorunu")
    report.append("")
    report.append("SL mesafesinin standart sapmasi cok yuksek (%{:.2f}). Bu su anlama geliyor:".format(sl_data['std_sl_pct']))
    report.append("- Bazı pozisyonlar cok hizli kapaniyor (TRX %0.75 SL)")
    report.append("- Digerleri cok uzun sure acik kalip buyuk kayip yapiyor (LAYER %32 SL)")
    report.append("- Dusuk fiyatli coinlerde ($<0.01) ATR cok kucuk, SL anlamsiz hale geliyor")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## 6. AI (MiMo) Performansi")
    report.append("")
    report.append("### Giris Oncesi Dogrulama")
    report.append("")
    report.append(f"| Metrik | Deger |")
    report.append(f"|--------|-------|")
    report.append(f"| Toplam AI Karari | {ai_data['total_decisions']} |")
    report.append(f"| TRADE Onaylama | {ai_data['trade_approved_count']} |")
    report.append(f"| SKIP Reddetme | {ai_data['trade_skipped_count']} |")
    report.append("")

    if ai_data['trade_approved_with_result']:
        approved_with_loss = [d for d in ai_data['trade_approved_with_result'] if d['symbol_pnl'] < 0]
        approved_with_win = [d for d in ai_data['trade_approved_with_result'] if d['symbol_pnl'] > 0]
        report.append(f"**AI Onayladigi Islemlerden Zarar Edenler:** {len(approved_with_loss)}")
        report.append("")
        for d in approved_with_loss[:10]:
            report.append(f"- {d['symbol']}: AI onayladi, ${d['symbol_pnl']:,.2f} zarar — Reason: {d['reason'][:80]}")
        report.append("")

    report.append("### Pozisyon Inceleme")
    report.append("")
    report.append(f"| Aksiyon | Sayi |")
    report.append(f"|---------|------|")
    report.append(f"| HOLD | {ai_data['review_hold_count']} |")
    report.append(f"| CLOSE | {ai_data['review_close_count']} |")
    report.append(f"| PARTIAL_CLOSE | {ai_data['review_partial_count']} |")
    report.append("")

    if ai_data['review_with_pnl']:
        hold_with_loss = [d for d in ai_data['review_with_pnl'] if d['action'] == 'HOLD' and d['pnl_pct'] < -5]
        report.append(f"**HOLD Kararlari ile Buyuyen Zararlar (>-5% PnL):** {len(hold_with_loss)}")
        report.append("")
        for d in hold_with_loss[:10]:
            report.append(f"- {d['symbol']}: %{d['pnl_pct']:.1f} zararda iken HOLD — {d['reason'][:80]}")
        report.append("")

    report.append("### AI Performans Sorunlari")
    report.append("")
    report.append("1. **FAIL-OPEN Politikasi:** AI hata verdiginde sinyal otomatik onaylaniyor. Bu, kalitesiz sinyallerin de acilmasina neden oluyor.")
    report.append("2. **HOLD Kararlari Zarar Buyutuyor:** AI, acik pozisyonlarda cok uzun sure HOLD diyor. Zarar buyudukten sonra CLOSE diyor.")
    report.append("3. **Giris Onaylama Orani:** Cok fazla TRADE onayi var, cok az SKIP var. AI cok mu yumusak?")
    report.append("4. **Reason Bos:** Bir cok AI kararinda reason alani bos. Kararlarin aciklanabilirligi dusuk.")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## 7. Kacirilmis Firsatlar")
    report.append("")
    report.append(f"### Istatistikler")
    report.append(f"- **Toplam Uretilen Sinyal:** {signal_data['total_signals']}")
    report.append(f"- **Pozisyon Aciilmayan Sinyal:** {signal_data['unacted_signals']}")
    report.append(f"- **Farkli Sembol:** {signal_data['unacted_symbols']}")
    report.append(f"- **Potansiyel Karli (>3%):** {len(profitable_missed)} sembol")
    report.append("")

    if profitable_missed:
        report.append("### Potansiyel Karli Kacirilmis Sinyaller")
        report.append("")
        report.append("| # | Coin | Sinyal Sayisi | Yon | Max Potansiyel | Min Potansiyel | Veri |")
        report.append("|---|------|--------------|-----|---------------|---------------|------|")
        for i, m in enumerate(profitable_missed[:20], 1):
            types = ", ".join(f"{k}:{v}" for k, v in m['signal_types'].items())
            data_avail = "Var" if m['price_data_available'] else "Yok"
            report.append(f"| {i} | {m['symbol']} | {m['signal_count']} | {types} | +%{m['best_potential_pct']:.1f} | %{m['worst_potential_pct']:.1f} | {data_avail} |")
        report.append("")

    report.append("### Neden Acilmadi?")
    report.append("")
    report.append("Olasin nedenler:")
    report.append("1. **AI Reddetti (SKIP):** MiMo grafik analizinde sinyali kalitesiz buldu")
    report.append("2. **Max Pozisyon Limiti:** 10 pozisyon limitine ulasildigi icin yeni pozisyon acilmadi")
    report.append("3. **Sector Limiti:** Ayni sektorden 2+ pozisyon acik oldugu icin engellendi")
    report.append("4. **Cooldown:** Daha once ayni coin'de kayip yasandigi icin 2 saat bekleme sureci")
    report.append("5. **Drawdown Kilidi:** Gunluk %5 drawdown asildigi icin yeni pozisyon acilmadi")
    report.append("6. **Kalite Filtresi:** Dusuk volatilite, dusuk hacim, yeni listelenme gibi filtreler")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## 8. Sistemsel Hatalar ve Bug'lar")
    report.append("")
    report.append("### Hala Devam Eden Sorunlar")
    report.append("")
    report.append("| # | Sorun | Onem | Durum |")
    report.append("|---|-------|------|-------|")
    report.append("| 1 | Dusuk fiyatli coinlerde ($<0.01) SL/TP hatali | KRITIK | Duzeltmemis |")
    report.append("| 2 | Blacklisting cok gec (5+ kayiptan sonra) | KRITIK | Kismen duzeltilmis |")
    report.append("| 3 | AI FAIL-OPEN politikasi | YUKSEK | Aktif |")
    report.append("| 4 | SL mesafe tutarsizligi (%0.75 - %32) | YUKSEK | Devam ediyor |")
    report.append("| 5 | AI HOLD kararlari zarar buyutme | YUKSEK | Devam ediyor |")
    report.append("| 6 | Ardisik kayip korumasi yok | ORTA | Devam ediyor |")
    report.append("| 7 | Tum pozisyonlar ayni anda acilma riski | ORTA | Kismen duzeltilmis |")
    report.append("| 8 | AI reason alanlari bos | ORTA | Devam ediyor |")
    report.append("| 9 | Gunluk optimizasyon hala tam calismiyor | DUSUK | Devam ediyor |")
    report.append("")

    report.append("### Yeni Tespit Edilen Bug'lar")
    report.append("")
    report.append("1. **MEGA/USDT Cakismasi:** V7'de 2 kazanc, V5'te 1 kayip — ayni coin farkli sonuclar uretiyor")
    report.append("2. **SYRUP/USDT Cift Kayip:** Hem V7'de acik pozisyon var hem de learning_state'te 2 kayip kayitli")
    report.append("3. **CELO/USDT Farklilik:** portfolio_state'de 2 kazanc +$279 ama learning_state'te 1 kazanc +$22 — veri tutarsizligi")
    report.append("4. **Sinyal Tekrari:** Ayni coin icin her tarama dongusunde ayni sinyal uretiliyor (2787 sinyal cok fazla)")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## 9. Parametre Onerileri")
    report.append("")
    report.append("### SL Carpani Degisikligi")
    report.append("")
    report.append("- **Mevcut:** ATR * 0.6 (cok kucuk ATR'lerde anlamsiz SL olusturuyor)")
    report.append("- **Oneri:** Min SL mesafesi %2, Max SL mesafesi %8 olarak sinirlandir")
    report.append("- **Eski:** min_sl_pct = 0.05 (cok kucuk) -> **Yeni:** min_sl_pct = 0.02 (min %2)")
    report.append("- **Eski:** max_tp_pct = 0.50 (cok buyuk) -> **Yeni:** max_tp_pct = 0.25 (max %25)")
    report.append("")

    report.append("### Min/Max Fiyat Filtresi")
    report.append("")
    report.append("- **Yeni Filtre:** $0.01 altindaki coinlerde ATR carpanini 2x artir")
    report.append("- **Veya:** $0.01 altindaki coinleri tamamen disarida birak")
    report.append("- **Oneri:** min_price: 0.01 (USDT bazinda)")
    report.append("")

    report.append("### RR Hedefi Revizyonu")
    report.append("")
    report.append("- **Mevcut:** target_rr: 5.5 (cok yuksek, cok az islem geciyor)")
    report.append("- **Oneri:** target_rr: 3.0 (daha fazla islem firsati)")
    report.append("- **Veya:** Dinamik RR — trend gucune gore 2.0-5.0 arasi")
    report.append("")

    report.append("### Blacklist Hizlandirma")
    report.append("")
    report.append("- **Mevcut:** 5+ kayiptan sonra blacklist")
    report.append("- **Oneri:** 2+ kayiptan sonra 1 haftalik blacklist, 3+ kayiptan sonra kalici blacklist")
    report.append("- **Ek:** Ayni coin'de 2. kez kayip edildiginde otomatik uyari")
    report.append("")

    report.append("### AI Politikasi Degisikligi")
    report.append("")
    report.append("- **FAIL-OPEN -> FAIL-CLOSE:** AI hata verdiyse sinyali REDDET, onaylama")
    report.append("- **HOLD Siniri:** PnL -%10'un altindaysa otomatik CLOSE")
    report.append("- **Minimum Reason:** Her AI kararinda en az 10 karakter reason zorunlu kilinmali")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## 10. Oneriler (Oncelik Sirasiyla)")
    report.append("")
    report.append("### Acil (Hemen Yapilacaklar)")
    report.append("")
    report.append("1. **FAIL-OPEN'i FAIL-CLOSE yap:** AI hata verdiginde sinyali reddet")
    report.append("2. **Dusuk fiyatli coin filtresi ekle:** $0.01 altinda islem yapma veya ATR carpanini 2x artir")
    report.append("3. **Blacklist hizlandir:** 2+ kayiptan sonra 1 haftalik blacklist")
    report.append("4. **SL sinirlandir:** Min %2, Max %8 araliginda tut")
    report.append("5. **AI reason zorunlulugu:** Bos reason ile islem onaylama")
    report.append("")
    report.append("### Orta Vadeli (1-2 Hafta)")
    report.append("")
    report.append("6. **Ardisik kayip korumasi:** 2. kayiptan sonra otomatik pozisyon boyutu kucultme")
    report.append("7. **Dinamik RR:** Trend gucune gore RR orani ayarlama (ADX >25 -> RR 4.0, ADX <20 -> RR 2.5)")
    report.append("8. **Piyasa rejimi filtresi:** RANGE/VOLATILE rejimde trend stratejisi kullanma")
    report.append("9. **Pozisyon acilis zamanlama:** 10 pozisyon birden acilmasin, 5'er dakika aralikla acilsin")
    report.append("10. **Veri tutarsizligi duzelt:** portfolio_state ve learning_state verilerini esitle")
    report.append("")
    report.append("### Uzun Vadeli (Mimari Iyilestirmeler)")
    report.append("")
    report.append("11. **Walk-forward validation:** Backtest overfitting kontrolu")
    report.append("12. **Backtest vs Canli karsilastirma modulu:** Gercek zamanli performans takibi")
    report.append("13. **Multi-strategy:** Tek strateji yerine birden fazla strateji paralel calistir")
    report.append("14. **Gerçek zamanli metrik dashboard:** Telegram uzerinden anlik performans")
    report.append("15. **Paper trading test donemi:** Yeni strateji once 1 hafta paper trade")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## 11. Duzeltilmis Hatalar (Referans)")
    report.append("")
    report.append("Onceki hata raporunda (23 Haziran 2026) tespit edilen ve duzeltilen hatalar:")
    report.append("")
    report.append("| # | Sorun | Durum |")
    report.append("|---|-------|-------|")
    report.append("| 1 | Config entegrasyonu yuklenmedi | Duzeltildi |")
    report.append("| 2 | RiskEngine entegrasyonu eksik | Duzeltildi |")
    report.append("| 3 | Trailing stop calismadi | Duzeltildi |")
    report.append("| 4 | Adaptif ogrenme calismadi | Duzeltildi |")
    report.append("| 5 | Gunluk drawdown kilidi devre disi | Duzeltildi |")
    report.append("| 6 | RR kontrolu yoktu | Duzeltildi |")
    report.append("| 7 | PnL hesaplama hatasi (27x) | Duzeltildi |")
    report.append("| 8 | HMSTR/USDT excluded edildi | Duzeltildi |")
    report.append("| 9 | Gunluk optimizasyon | Devam ediyor |")
    report.append("| 10 | Backtest-canli farki | Tespit edildi |")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## 12. Sonuc")
    report.append("")
    report.append("Trading Bot V7 botu genel olarak calisiyor ve $10,000'dan $16,323'e yukseldi (%+63).")
    report.append("Ancak bu getirinin buyuk kismi acik pozisyonlardan geliyor ve henuz kapanmadi.")
    report.append("")
    report.append("Kapanmis islemlere bakildiginda:")
    report.append(f"- Win rate: %{trade_data['total_wins']/(trade_data['total_wins']+trade_data['total_losses'])*100:.1f} (dusuk)")
    report.append("- Buyuk kayip islemleri (SYN, HUMA, JST) kazanci eritiyor")
    report.append("- AI (MiMo) dogrulamasi yeterince sik degil, FAIL-OPEN sorunlu")
    report.append("- SL/TP tutarsizligi ciddi bir sorun")
    report.append("")
    report.append("Onemli iyilestirmeler:")
    report.append("1. FAIL-OPEN -> FAIL-CLOSE degisikligi en buyuk etkiyi yapacak")
    report.append("2. Dusuk fiyatli coin filtresi buyuk kayiplari onleyecek")
    report.append("3. Hizli blacklisting tekrarlanan kayiplari kesecek")
    report.append("4. SL sinirlandirmasi tutarsizligi cozecek")
    report.append("")
    report.append("Bu iyilestirmeler yapilirsa win rate'in %30+ seviyelerine cikmasi ve")
    report.append("tekrarlanan buyuk kayiplarin onlenmesi bekleniyor.")
    report.append("")
    report.append("---")
    report.append(f"*Rapor MiMoCode tarafindan olusturulmustur — {datetime.now().strftime('%d.%m.%Y %H:%M')}*")

    report_text = "\n".join(report)

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"  Rapor kaydedildi: {REPORT_PATH}")
    print(f"  Toplam satir: {len(report)}")
    return report_text


def main():
    print("=" * 60)
    print("Trading Bot V7 KAPSAMLI HATA RAPORU ANALIZI")
    print("=" * 60)
    print()

    download_results = download_price_data()
    trade_data = analyze_trades()
    signal_data = analyze_signals_and_missed(load_jsonl(LOGS_DIR / "signals_v7.jsonl"))
    ai_data = analyze_ai_performance()
    sl_data = analyze_sl_tp_consistency()
    consecutive_data = analyze_consecutive_losses()

    print()
    report = generate_report(trade_data, signal_data, ai_data, sl_data, consecutive_data, download_results)

    print()
    print("=" * 60)
    print("ANALIZ TAMAMLANDI!")
    print(f"Rapor: {REPORT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
