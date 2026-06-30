# -*- coding: utf-8 -*-
"""
src/strategy/coin_quality_filter.py — Coin Kalite Filtresi
Gecmis performansa gore coin secimi ve pozisyon boyutlandirma.
"""

class CoinQualityFilter:
    """
    Her coin icin gecmis performans istatistikleri tutar.
    Kaliteli coinleri belirler ve pozisyon buyuklugunu ayarlar.
    """

    def __init__(self, min_trades: int = 3, min_win_rate: float = 0.30):
        self.coin_stats = {}
        self.min_trades = min_trades
        self.min_win_rate = min_win_rate

    def update_stats(self, symbol: str, win_rate: float, avg_pnl: float, total_trades: int):
        """Coin istatistiklerini guncelle."""
        self.coin_stats[symbol] = {
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'trades': total_trades,
        }

    def should_trade(self, symbol: str) -> bool:
        """Bu coin'de islem yapilip yapilmayacagina karar ver."""
        stats = self.coin_stats.get(symbol)

        # Istatistik yoksa izin ver (yeni coin)
        if stats is None:
            return True

        # Yeterli islem yoksa izin ver
        if stats['trades'] < self.min_trades:
            return True

        # Win rate cok dusukse kapat
        if stats['win_rate'] < self.min_win_rate:
            return False

        return True

    def get_position_size_multiplier(self, symbol: str) -> float:
        """
        Pozisyon buyuklugu carpani.
        Iyi performing coinlerde daha buyuk, kotulerde daha kucuk.
        """
        stats = self.coin_stats.get(symbol)

        if stats is None or stats['trades'] < self.min_trades:
            return 1.0  # Varsayilan

        wr = stats['win_rate']

        if wr >= 0.50:
            return 1.5   # Cok iyi -> buyuk pozisyon
        elif wr >= 0.40:
            return 1.25  # Iyi -> biraz buyuk
        elif wr >= 0.30:
            return 1.0   # Normal
        elif wr >= 0.20:
            return 0.5   # Kucuk
        else:
            return 0.0   # Cok kotu -> hic acma

    def get_all_stats(self) -> dict:
        """Tum coin istatistiklerini dondur."""
        return self.coin_stats.copy()

    def get_top_coins(self, n: int = 5) -> list:
        """En iyi N coin'i dondur."""
        sorted_coins = sorted(
            self.coin_stats.items(),
            key=lambda x: x[1]['win_rate'],
            reverse=True
        )
        return [coin for coin, _ in sorted_coins[:n]]

    def get_worst_coins(self, n: int = 5) -> list:
        """En kotu N coin'i dondur."""
        sorted_coins = sorted(
            self.coin_stats.items(),
            key=lambda x: x[1]['win_rate']
        )
        return [coin for coin, _ in sorted_coins[:n]]
