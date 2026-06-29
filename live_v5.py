# -*- coding: utf-8 -*-
"""
live_v5.py — V5 Price Action LIVE Bot (Filtresiz, %2 Risk)
"""
import sys
import os
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np
import yaml

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

from src.data.historical import HistoricalDataFetcher
from src.strategy.v5_pa_strategy import V5PriceActionStrategy
from src.strategy.regime_detector import RegimeDetector, MarketRegime
from src.risk.engine import RiskEngine
from src.utils.telegram_notifier import send_telegram_notification
from src.utils.logger import get_logger
from src.config.settings import get_settings
from src.utils.telegram_listener import start_telegram_listener

logger = get_logger("live_v5")


def format_price(price):
    if price is None or price == 0: return "-"
    if price >= 100: return f"${price:,.2f}"
    elif price >= 1.0: return f"${price:,.4f}"
    elif price >= 0.0001: return f"${price:,.6f}"
    else: return f"${price:,.8f}"


class LiveV5Bot:
    """V5 Price Action — Filtresiz, %2 risk, 50 coin."""

    EXCLUDED = {"PAXG/USDT", "RLUSD/USDT", "FDUSD/USDT", "USDC/USDT"}

    def __init__(self, initial_capital=10000.0, max_positions=5, position_pct=0.02,
                 is_live=False, top_n=50):
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.position_pct = position_pct
        self.is_live = is_live
        self.top_n = top_n

        # Config'den strateji parametrelerini yükle
        cfg = self._load_config()
        strat_cfg = cfg.get("strategy", {})
        risk_cfg = cfg.get("risk", {})
        exec_cfg = cfg.get("execution", {})

        self.fetcher = HistoricalDataFetcher()
        self.strategy = V5PriceActionStrategy(
            sweep_window=strat_cfg.get("sweep_window", 100),
            max_hold_sweep=strat_cfg.get("max_hold_sweep", 7),
            target_rr=strat_cfg.get("target_rr", 5.5),
            trend_ema=strat_cfg.get("trend_ema", 180),
            atr_multiplier=strat_cfg.get("atr_multiplier", 0.6),
            use_premium_discount=strat_cfg.get("use_premium_discount", True),
            max_tp_pct=strat_cfg.get("max_tp_pct", 0.50),
            min_sl_pct=strat_cfg.get("min_sl_pct", 0.05),
        )
        self.balance = initial_capital
        self.positions = {}
        self._symbol_stats = {}
        self._cooldown_map = {}
        self.trades = []

        # Config'den risk parametrelerini yükle
        self.max_daily_drawdown_pct = risk_cfg.get("max_daily_drawdown_pct", 0.05)
        self.min_risk_reward_ratio = risk_cfg.get("min_risk_reward_ratio", 5.5)
        self.leverage = exec_cfg.get("leverage", 5)
        self.commission_rate = cfg.get("paper_trading", {}).get("commission_rate", 0.00063)

        # RiskEngine
        self.risk_engine = RiskEngine(initial_balance=initial_capital)

        self._load_state()

        self.settings = get_settings()
        self.settings.strategy.version = "v5"

        print(f"[V5] Baslatildi | ${initial_capital:,.0f} | {'LIVE' if is_live else 'PAPER'} | Top {top_n}")
        print(f"[V5] Config: sweep={self.strategy.sweep_window} hold={self.strategy.max_hold_sweep} rr={self.strategy.target_rr} ema={self.strategy.trend_ema}")
        send_telegram_notification(
            f"🤖 V5 PA Bot Başlatıldı\n"
            f"💰 Sermaye: ${initial_capital:,.2f}\n"
            f"📊 Mod: {'🔴 CANLI' if is_live else '🟢 PAPER'}\n"
            f"🎯 Max Pozisyon: {max_positions}\n"
            f"📏 Risk: %{position_pct*100:.0f}\n"
            f"📋 Semboller: Top {top_n}\n"
            f"🛡️ RR: {self.strategy.target_rr} | ATR Stop: {self.strategy.atr_multiplier}x\n"
            f"⚙️ Filtre: YOK (filtresiz)"
        )

        # Listener run_all_bots.py tarafindan tek seferlik baslatilir

    def _load_config(self) -> dict:
        """config_v7.yaml dosyasından parametreleri yükler."""
        config_path = Path("config_v7.yaml")
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Config yüklenemedi: {e}")
        return {}

    def _print_status(self):
        """Konsola durum yaz."""
        print(f"[V5] Bakiye: {format_price(self.balance)} | Pozisyon: {len(self.positions)}/{self.max_positions}")
        for sym, pos in self.positions.items():
            print(f"  {pos['t']} {sym} @ {format_price(pos['e'])} | SL:{format_price(pos['sl'])} TP:{format_price(pos['tp'])}")

    def get_durum_text(self) -> str:
        """Telegram /durum komutu icin V5 ozeti uret — anlık K/Z dahil."""
        lines = []
        lines.append(f"🤖 [V5] DURUM")
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"💰 Bakiye: {format_price(self.balance)}")
        initial = self.initial_capital
        getiri = (self.balance / initial - 1) * 100
        lines.append(f"📊 Getiri: %{getiri:+.1f}")
        lines.append(f"🔓 Açık Pozisyon: {len(self.positions)}/{self.max_positions}")
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        total_unrealized = 0.0
        if not self.positions:
            lines.append("  Açık pozisyon yok")
        else:
            for sym, pos in self.positions.items():
                direction = pos.get('t', '?')
                entry = pos.get('e', 0)
                sl = pos.get('sl', 0)
                tp = pos.get('tp', 0)
                notional = pos.get('n', 0)
                sz = pos.get('sz', 0)
                try:
                    ticker = self.fetcher.exchange.fetch_ticker(sym)
                    current = float(ticker['last'])
                except Exception:
                    current = entry
                if direction == 'BUY':
                    pnl_usd = (current - entry) * sz * self.leverage
                    pnl_pct = (current - entry) / entry * 100 if entry else 0
                else:
                    pnl_usd = (entry - current) * sz * self.leverage
                    pnl_pct = (entry - current) / entry * 100 if entry else 0
                total_unrealized += pnl_usd
                yon_emoji = "🟢" if direction == "BUY" else "🔴"
                kz_emoji = "📈" if pnl_usd >= 0 else "📉"
                lines.append(f"  {yon_emoji} {sym} | {direction}")
                lines.append(f"     Giriş: {format_price(entry)} → Şimdi: {format_price(current)}")
                lines.append(f"     {kz_emoji} K/Z: ${pnl_usd:+.2f} (%{pnl_pct:+.1f})")
                lines.append(f"     SL: {format_price(sl)} | TP: {format_price(tp)}")
                lines.append(f"     Büyüklük: {sz:.2f} adet | Değer: {format_price(notional)}")
                lines.append("")
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📊 Açık Pozisyon K/Z: {format_price(total_unrealized)}")
        lines.append(f"💼 Toplam: {format_price(self.balance + total_unrealized)}")
        return "\n".join(lines)

    def _send_portfolio_summary(self, msg=""):
        send_telegram_notification(self.get_durum_text())

    def _load_state(self):
        try:
            p = Path("logs/portfolio_state_v5.json")
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    s = json.load(f)
                self.balance = s.get("balance", self.initial_capital)
                self.positions = s.get("positions", {})
                self._symbol_stats = s.get("symbol_stats", {})
        except Exception:
            pass

    def _save_state(self):
        try:
            Path("logs").mkdir(exist_ok=True)
            with open("logs/portfolio_state_v5.json", "w", encoding="utf-8") as f:
                json.dump({"balance": self.balance, "positions": self.positions,
                           "symbol_stats": self._symbol_stats}, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _is_in_cooldown(self, symbol):
        if symbol not in self._cooldown_map: return False, ""
        cd = self._cooldown_map[symbol]
        now = pd.Timestamp.now(tz="UTC").tz_localize(None)
        if now < cd["until"]:
            return True, f"Cooldown: {cd['reason']}"
        del self._cooldown_map[symbol]
        return False, ""

    def _set_cooldown(self, symbol, reason, hours=2):
        now = pd.Timestamp.now(tz="UTC").tz_localize(None)
        self._cooldown_map[symbol] = {"until": now + timedelta(hours=hours), "reason": reason}

    def run_cycle(self):
        print(f"\n[V5] Tarama | Bakiye: {format_price(self.balance)} | Pozisyon: {len(self.positions)}")
        newly_opened = []  # Bu döngüde açılan pozisyonları topla

        # Pozisyon izle + trailing stop
        for sym in list(self.positions.keys()):
            pos = self.positions[sym]
            try:
                ticker = self.fetcher.exchange.fetch_ticker(sym)
                price = ticker["last"]

                # Trailing stop güncelle
                try:
                    df_atr = self.fetcher.fetch_ohlcv(sym, "1h", limit=20)
                    if not df_atr.empty and len(df_atr) >= 14:
                        high_low = df_atr["high"] - df_atr["low"]
                        high_close = (df_atr["high"] - df_atr["close"].shift(1)).abs()
                        low_close = (df_atr["low"] - df_atr["close"].shift(1)).abs()
                        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                        atr_val = float(tr.rolling(window=14).mean().iloc[-1])
                        if atr_val > 0:
                            side = "LONG" if pos["t"] == "BUY" else "SHORT"
                            new_sl = self.risk_engine.calculate_dynamic_trailing(
                                entry_price=pos["e"],
                                current_price=price,
                                original_sl=pos["sl"],
                                side=side,
                                atr=atr_val,
                            )
                            if new_sl != pos["sl"]:
                                pos["sl"] = new_sl
                                print(f"[V5] {sym} trailing stop: {format_price(new_sl)}")
                except Exception:
                    pass

                hit_sl = (pos["t"]=="BUY" and price<=pos["sl"]) or (pos["t"]=="SELL" and price>=pos["sl"])
                hit_tp = (pos["t"]=="BUY" and price>=pos["tp"]) or (pos["t"]=="SELL" and price<=pos["tp"])

                if hit_sl or hit_tp:
                    self._close(sym, price, "SL" if hit_sl else "TP")
            except Exception:
                pass

        # Günlük drawdown kontrolü
        current_dd = self.risk_engine.get_daily_drawdown_pct()
        if current_dd >= self.max_daily_drawdown_pct:
            print(f"[V5] Drawdown kilidi: %{current_dd*100:.2f}. Yeni pozisyon açılmıyor.")
            self._save_state()
            return

        # Tarama
        try:
            symbols = self.fetcher.fetch_top_symbols(top_n=self.top_n, quote="USDT")
            if not symbols:
                return

            for sym in symbols:
                if sym in self.EXCLUDED: continue
                if sym in self.positions: continue
                if len(self.positions) >= self.max_positions: break
                in_cooldown, _ = self._is_in_cooldown(sym)
                if in_cooldown: continue

                try:
                    for tf in ["15m", "1h", "4h"]:
                        df = self.fetcher.fetch_ohlcv(sym, tf, limit=500)
                        if df.empty or len(df) < 200: continue

                        df_sig = self.strategy.calculate_signals(df)
                        for i in range(max(0, len(df_sig)-15), len(df_sig)):
                            sig = df_sig.iloc[i]["signal"]
                            if sig in ("BUY", "SELL"):
                                try:
                                    ticker = self.fetcher.exchange.fetch_ticker(sym)
                                    live_price = float(ticker["last"])
                                except Exception:
                                    live_price = float(df_sig.iloc[i]["close"])
                                sl_hist = float(df_sig.iloc[i]["sl_price"])
                                if sig == "BUY":
                                    risk = float(df_sig.iloc[i]["close"]) - sl_hist
                                    if risk <= 0: break
                                    sl = live_price - risk
                                    tp = live_price + (self.strategy.target_rr * risk)
                                else:
                                    risk = sl_hist - float(df_sig.iloc[i]["close"])
                                    if risk <= 0: break
                                    sl = live_price + risk
                                    tp = live_price - (self.strategy.target_rr * risk)
                                if tp <= 0: break

                                # RR kontrolü
                                if sig == "BUY":
                                    reward = tp - live_price
                                    risk_val = live_price - sl
                                else:
                                    reward = live_price - tp
                                    risk_val = sl - live_price
                                if risk_val > 0 and reward / risk_val < self.min_risk_reward_ratio:
                                    break

                                info = self._open(sym, sig, live_price, sl, tp)
                                if info:
                                    newly_opened.append(info)
                                break
                        if sym in self.positions: break
                except Exception:
                    pass

        except Exception as e:
            print(f"[V5] Tarama hatasi: {e}")

        # Yeni açılan pozisyonları tek mesajda gönder
        if newly_opened:
            lines = [f"🤖 [V5] {len(newly_opened)} YENİ POZİSYON AÇILDI"]
            lines.append(f"💰 Bakiye: {format_price(self.balance)} | Pozisyon: {len(self.positions)}/{self.max_positions}")
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            for p in newly_opened:
                yon_emoji = "🟢" if p["yon"] == "BUY" else "🔴"
                lines.append(f"{yon_emoji} {p['sym']} | {p['yon']}")
                lines.append(f"   Giriş: {format_price(p['price'])}  SL: {format_price(p['sl'])}  TP: {format_price(p['tp'])}")
                lines.append(f"   Değer: {format_price(p['notional'])}")
            # Açık pozisyonların toplam anlık K/Z'si
            total_unrealized = 0.0
            for sym, pos in self.positions.items():
                try:
                    ticker = self.fetcher.exchange.fetch_ticker(sym)
                    current = float(ticker['last'])
                    if pos['t'] == 'BUY':
                        total_unrealized += (current - pos['e']) * pos['sz'] * self.leverage
                    else:
                        total_unrealized += (pos['e'] - current) * pos['sz'] * self.leverage
                except Exception:
                    pass
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append(f"📊 Açık Pozisyon K/Z: {format_price(total_unrealized)}")
            send_telegram_notification("\n".join(lines))

        self._save_state()

    def _open(self, sym, direction, price, sl, tp):
        """Pozisyon acar. Basarili olursa pozisyon bilgisini dict olarak doner."""
        risk_pct = self.position_pct
        if direction == "BUY":
            risk = price - sl
        else:
            risk = sl - price
        if risk <= 0: return None

        risk_amount = self.balance * risk_pct
        sz = risk_amount / risk
        notional = sz * price
        if notional > self.balance * 0.1: return None

        self.positions[sym] = {"t": direction, "e": price, "sl": sl, "tp": tp, "sz": sz, "n": notional}
        self.balance -= notional * self.commission_rate
        print(f"[V5] {sym} {direction} @ {format_price(price)}")
        return {"sym": sym, "yon": direction, "price": price, "sl": sl, "tp": tp, "notional": notional}

    def _close(self, sym, exit_price, reason):
        pos = self.positions.pop(sym)
        entry = pos["e"]
        if pos["t"] == "BUY":
            pnl_usd = (exit_price - entry) * pos["sz"] * self.leverage
        else:
            pnl_usd = (entry - exit_price) * pos["sz"] * self.leverage
        commission = pos["n"] * self.commission_rate * self.leverage * 2
        pnl = pnl_usd - commission
        pnl_pct = pnl_usd / (entry * pos["sz"] * self.leverage) if entry * pos["sz"] * self.leverage > 0 else 0
        self.balance += pnl

        # Risk engine'e zararı kaydet
        if pnl < 0:
            self.risk_engine.record_loss(abs(pnl))
        self.risk_engine.set_balance(self.balance)

        if sym not in self._symbol_stats:
            self._symbol_stats[sym] = {"wins": 0, "losses": 0, "total_pnl": 0.0}
        self._symbol_stats[sym]["total_pnl"] += pnl
        if pnl > 0:
            self._symbol_stats[sym]["wins"] += 1
        else:
            self._symbol_stats[sym]["losses"] += 1
            self._set_cooldown(sym, "SL")

        cs = self._symbol_stats[sym]
        ct = cs["wins"] + cs["losses"]
        cwr = cs["wins"] / ct * 100 if ct else 0

        emoji = "✅" if pnl > 0 else "❌"
        send_telegram_notification(
            f"{emoji} [V5] POZİSYON KAPATILDI — {sym}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Yön: {pos['t']}\n"
            f"💰 Giriş: {format_price(entry)}\n"
            f"💵 Çıkış: {format_price(exit_price)}\n"
            f"📈 K/Z: {format_price(pnl)} (%{pnl_pct*100:+.1f})\n"
            f"📋 Neden: {reason}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 {sym}: {ct} işlem, %{cwr:.0f} WR, {format_price(cs['total_pnl'])}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Bakiye: {format_price(self.balance)}"
        )
        print(f"[V5] {sym} KAPATILDI {reason} | {format_price(pnl)}")

    def _print_status(self):
        print(f"[V5] Bakiye: {format_price(self.balance)} | Pozisyon: {len(self.positions)}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--paper", action="store_true")
    parser.add_argument("--interval", type=int, default=15)
    parser.add_argument("--capital", type=float, default=10000.0)
    parser.add_argument("--top-n", type=int, default=50)
    args = parser.parse_args()

    bot = LiveV5Bot(initial_capital=args.capital, max_positions=5,
                    position_pct=0.02, is_live=args.live and not args.paper, top_n=args.top_n)
    while True:
        try:
            bot.run_cycle()
        except Exception as e:
            print(f"[V5] Hata: {e}")
        time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
