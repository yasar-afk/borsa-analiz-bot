# Trading Bot Bot Hata Raporu — V5 & V7 İşlem Analizi

**Tarih:** 22 Haziran 2026
**Bot Çalışma Süresi:** ~17:18 - 23:43 (6.5 saat)
**Rapor Türü:** Hata analizi ve kök neden tespiti

---

## 1. ÖZET TABLO

| Bot | Başlangıç | Güncel | Kayıp/Kazanç | Kapalı İşlem | Açık Pozisyon | WR |
|-----|-----------|--------|---------------|--------------|---------------|-----|
| V7  | $10,000   | $10,054.90 | +$54.90 (+0.55%) | 3 (3 kayıp) | 10 | %0 |
| V5  | $10,000   | $9,499.02 | -$500.98 (-5.01%) | 1 (1 kayıp) | 5 | %0 |

**Toplam Kapanan İşlem: 4 — Hepsi ZARAR (%0 WR)**
**Silinen İşlem: 1 (HMSTR/USDT — API hatası nedeniyle pozisyon kapatıldı)**

---

## 2. KRİTİK HATALAR VE KÖK NEDENLER

### HATA 1: MEGA/USDT — $2,897.11 Tek İşlemde Büyük Kayıp (V7)
**Nedeni:**
- İlk SELL pozisyonu $0.05574'ten açıldı (17:20)
- Stop-loss $0.05674'teydi — sadece **%1.8% mesafe** (10000$'ın %2'si risk)
- Ancak pozisyon büyüklüğü **$5,797.77 notional** hesaplandı (5x kaldıraç ile)
- SL tetiklendiğinde kaldıraçlı zarar: ~$2,897

**Sorun:** V7 strategy parametreleri `sweep_window=100, max_hold_sweep=7` olarak ayarlanmış ama kodda `sweep_window=30, max_hold_sweep=20` default kullanılıyor. Config dosyası ile strateji kodu uyuşmuyor.

**Kök Neden:** `LiveV7Bot.__init__` metodunda `V7PriceActionStrategy()` parametresiz çağrılıyor — config'deki sweep_window=100, max_hold_sweep=7, atr_multiplier=0.6, volume_threshold=0.5 değerleri hiç yüklenmiyor. Varsayılan değerler (30, 20, 0.6, 0.3) kullanılıyor.

**Etki:** Strateji çok daha dar sweep penceresi ve daha uzun hold süresi ile çalışıyor — bu da daha fazla yanlış sinyal ve çok dar SL mesafelerine yol açıyor.

---

### HATA 2: Config ile Kod Uyuşmazlığı
**`live_v7.py:81`**: `self.strategy = V7PriceActionStrategy()` — parametre yok
**`config_v7.yaml:9-16`**: sweep_window=100, max_hold_sweep=7, volume_threshold=0.5

**Etkilenen dosyalar:**
- `live_v7.py` — config hiç yüklenmiyor
- `live_v5.py` — aynı sorun, config kullanılmıyor

---

### HATA 3: İlk Döngüde 10 Pozisyonun Tamamını Hemen Açma
**Olay:** İlk tarama döngüsünde 28 sinyal bulundu, 10'u hemen açıldı (17:20:36-45 arası — 9 saniye içinde)

**Sorun:** Hızlı açılış nedeniyle:
- Piyasa koşulları değerlendirilmeden üst üste pozisyon açıldı
- Korelasyon kontrolü yetersiz (V7'de sektörel limit var ama korelasyon engine kodu kullanılmıyor)
- İlk 10 pozisyon hepsi aynı anda — bir trend tersine dönerse hepsi birden etkilenir

**Kök Neden:** `open_position` metodunda pozisyon açılırken `RiskEngine.assess()` çağrılmıyor — sadece basit risk bütçesi hesaplanıyor.

---

### HATA 4: Çok Dar Stop-Loss Mesafeleri (V7)
Örnek hesaplamalar (ilk 10 pozisyondan):

| Coin | Giriş | SL | SL Mesafe | Risk % |
|------|-------|-----|-----------|--------|
| TRX/USDT SELL | $0.3319 | $0.3344 | $0.0025 | %0.75 |
| ID/USDT BUY | $0.0367 | $0.0345 | $0.0022 | %5.9 |
| RESOLV/USDT BUY | $0.0218 | $0.0148 | $0.0070 | %32.1 |
| LAYER/USDT BUY | $0.0793 | $0.0538 | $0.0255 | %32.1 |
| HMSTR/USDT BUY | $0.000184 | $0.000143 | $0.000041 | %22.3 |

**Sorun:** Bazı pozisyonlarda SL mesafesi çok geniş (%30+) — bu durumda bile tek bir kayıp sermayenin önemli bir kısmını siliyor. Diğer tarafta TRX gibi çok dar SL (%0.75) — çok çabuk tetikleniyor.

**Kök Neden:** ATR tabanlı SL hesaplaması `0.6x ATR` ile yapılıyor ama low-priced coinlerde (MEGA, HMSTR) ATR çok küçük — bu da ya çok dar ya da orantısız SL oluşturuyor.

---

### HATA 5: Pozisyon Boyutlandırma Sorunları (V5)
**`live_v5.py:251`**: `sz = (self.balance * risk_pct) / (risk / price * 5)`

Bu formülde risk_pct=%2, risk/price oranını 5x ile çarpıyor — bu kaldıraçlı boyutu hesaplıyor ama:
- Kaldıraçlı boyut, marjin gereksiniminden çok daha büyük olabiliyor
- `notional > balance * 0.1` kontrolü var ama zaten %10'luk sermaye limitini aşan pozisyonlar açılıyor

**Örnek:** V5 RESOLV/USDT — $2.73 notional (çok küçük, marjin limitinin altında) — bu pozisyon neredeyse anlamsız.

---

### HATA 6: Adaptif Öğrenme Çalışmıyor
**`learning_state.json`**: Tek bir optimizasyon çalışmış, hiçbir parametrik değişiklik yapmamış (`changes: []`), version hâlâ `v7.000`.

**Kök Neden:** `_run_daily_optimization` metodu `self.trades` listesinden learner'a veri aktarıyor ama `self.trades` hiçbir zaman doldurulmuyor — pozisyon kapatıldığında `_close_position` sadece `_symbol_stats` ve `learner.update_symbol_stats` çağrıyor, `self.trades`'e TradeRecord eklemiyor.

---

### HATA 7: Trailing Stop Loss Çalışmıyor
`RiskEngine.calculate_dynamic_trailing` fonksiyonu mevcut ama hiçbir yerde çağrılmıyor — ne `monitor_positions`'ta ne de `_close_position`'da.

**Sonuç:** Fiyat kârdayken bile SL sabit kalıyor — kâr korunamıyor.

---

### HATA 8: Günlük Drawdown Kontrolü Devre Dışı
`RiskEngine`'de `max_daily_drawdown_pct: %5` ayarlı — V7 tek bir MEGA işleminde $2,897 kaybetti (%29). Buna rağmen yeni pozisyonlar açılmaya devam etti.

**Kök Neden:** RiskEngine, LiveV7Bot/LiveV5Bot tarafından kullanılmıyor — her iki bot da kendi basit risk hesaplamasını yapıyor.

---

### HATA 9: V7'de Tekrarlı Sinyal Taraması
Her tarama döngüsünde (15 dk) aynı semboller için tekrar sinyal üretiliyor — örneğin MEGA/USDT her taramada BUY sinyali veriyor ama pozisyon zaten açık. Sinyal üretimi durdurulmuyor.

---

### HATA 10: HMSTR/USDT — Geçersiz Coin, Silinmesi Gereken İşlem (V7)
**Olay:** HMSTR/USDT 22 Haziran 2026'da V7 botu tarafından BUY sinyali ile pozisyon olarak açıldı (entry: $0.0001838, notional: $911.52).

**Sorunlar:**
1. **Fiyat çok düşük ($0.0001838)** — ATR tabanlı SL hesaplaması bu fiyat aralığında anlamsız sonuçlar üretiyor. İlk açılışta SL $0.000143 idi (%22.3 mesafe), ancak sonraki taramalarda SL $0.000178-0.000185 aralığına kaydı — bu da SL'nin giriş fiyatına çok yakın olması anlamına geliyor.
2. **API hatası — fiyat alınamıyor:** 23 Haziran 00:15'ten itibaren her 15 dakikada bir `HMSTR/USDT fiyat kontrolü hatası` loglanıyor. Binance API'si bu sembol için ticker verisi dönemiyor — muhtemelen coin delist edildi veya geçici olarak askıya alındı.
3. **Pozisyon kapatılamıyor:** Fiyat alınamadığı için stop-loss veya take-profit tetiklenemiyor — pozisyon süresiz açık kalıyor.
4. **Her taramada tekrar sinyal üretiyor:** HMSTR/USDT her tarama döngüsünde BUY sinyali veriyor (273+ kez loglandı) ama pozisyon zaten açık — gereksiz API çağrısı ve log kirliliği.

**Kök Neden:** 
- Düşük fiyatlı coinlerde ($<0.01) filtre yetersiz — min_volatility_pct=0.3 ama bu coin çok düşük fiyatta olduğu için volatilite filtresiypass ediyor.
- Coin delist/asıkya alma durumunda pozisyon otomatik kapatma mekanizması yok.
- `EXCLUDED_SYMBOLS` listesinde HMSTR yok.

**Etki:** $911.52 notional pozisyon süresiz açık, her döngüde API hatası üretiliyor, bakiye bloke.

**Düzeltme:** HMSTR/USDT portfolio_state_v7.json'dan silindi, pozisyon kapatıldı.

---

### HATA 11: Backtest Canlı Performans Farkı
**Backtest:** %114 ROI, %26.6 WR (100 coin)
**Canlı (ilk 6 saat):** %0 WR, tek büyük kayıp

**Kök Neden:** Backtest'te:
- Geçmiş verilerle optimizasyon yapılmış (overfitting riski)
- Slippage ve komisyon yeterince model edilmemiş
- Canlı piyasa koşulları (haberler, likidite) farklı
- Backtest'te tüm sinyaller uygulanıyor, canlıda sadece ilk 10

---

## 3. AÇIK POZİSYONLARIN DURUMU

### V7 — 10 Açık Pozisyon (Güncel Durum)
Saat 23:43 itibarıyla hiçbir pozisyon SL veya TP'ye ulaşmamış — hepsi süresiz açık bekliyor.

**Risk:** Piyasa tersine dönerse 10 pozisyonun tamamı SL'ye uğrayabilir — toplam risk ~$3,000+.

### V5 — 5 Açık Pozisyon
- MEGA/USDT SELL — V7 ile aynı coin, zaten zararda
- TON/USDT SELL — SL çok geniş (%8.7%), uzun vadeli beklenti
- DOGE/USDT SELL — SL %2 mesafede
- SUI/USDT BUY — SL %7.5 mesafede
- RESOLV/USDT BUY — $2.73 notional (anlamsız büyüklük)

---

## 4. TELEGRAM HATALARI

1. **17:57:43** — `Remote end closed connection without response` — geçici bağlantı hatası
2. **21:00:41** — `getaddrinfo failed` — DNS çözümleme hatası (internet kesintisi)

**Etki:** Bildirimler iple gönderilemedi — pozisyon kapatma/kar alma bildirimleri kaçırılmış olabilir.

---

## 5. ÖNERİLER

### Acil (Önemli):
1. **Config entegrasyonu:** `LiveV7Bot.__init__` ve `LiveV5Bot.__init__` config dosyalarından parametreleri okumalı
2. **RiskEngine entegrasyonu:** Pozisyon açmadan önce `RiskEngine.assess()` çağrılmalı
3. **Max pozisyon limiti:** İlk döngüde 10 pozisyon birden açılmasını engelleme (max 3-4/start)
4. **Trailing stop aktifleştirme:** `monitor_positions` içinde `calculate_dynamic_trailing` kullanılmalı

### Orta Vadeli:
5. **Adaptif öğrenme düzeltmesi:** `self.trades` listesine TradeRecord eklenmeli
6. **Günlük drawdown kilidi:** Drawdown %5'i aştığında pozisyon açılması durdurulmalı
7. **Düşük fiyatlı coin filtre:** <$0.01 fiyatlı coinlerde volatilite filtresi artırılmalı

### Uzun Vadeli:
8. **Backtest Overfitting kontrolü:** Walk-forward validation ile doğrulama
9. **Backtest vs canlı karşılaştırma modülü**
10. **Piyasa rejimi bazlı pozisyon açma limiti:** VOLATILE rejimde max pozisyon sayısı düşürülmeli

---

## 6. DÜZELTMELER (23 Haziran 2026)

### Yapılan Düzeltmeler:

| # | Düzeltme | Dosya | Durum |
|---|----------|-------|-------|
| 1 | Config entegrasyonu — strateji parametreleri config_v7.yaml'dan yükleniyor | `live_v7.py`, `live_v5.py` | ✅ |
| 2 | RiskEngine entegrasyonu — drawdown kontrolü, RR kontrolü aktif | `live_v7.py`, `live_v5.py` | ✅ |
| 3 | Trailing stop aktifleştirme — monitor_positions'da dinamik SL güncellemesi | `live_v7.py`, `live_v5.py` | ✅ |
| 4 | Adaptif öğrenme düzeltmesi — self.trades listesine TradeRecord ekleniyor | `live_v7.py` | ✅ |
| 5 | Günlük drawdown kilidi — %5 aşıldığında pozisyon açma engelleniyor | `live_v7.py`, `live_v5.py` | ✅ |
| 6 | RR kontrolü — minimum risk/ödül oranı kontrol ediliyor | `live_v7.py`, `live_v5.py` | ✅ |
| 7 | Config dosyası eklendi — src/strategy/feature_weights.py | `src/strategy/feature_weights.py` | ✅ |
| 8 | **KRİTİK: PnL hesaplama hatası düzeltildi** — düşük fiyatlı coinlerde 27x fazla zarar hesabı yapılıyordu | `live_v7.py`, `live_v5.py`, `run_all_bots.py` | ✅ |
| 9 | **FAIL-OPEN → FAIL-CLOSE** — AI hata verdiğinde sinyal artık REDDEDİLİR, onaylanmaz | `ai_chart_verifier.py` | ✅ |
| 10 | **Entry prompt sıkılaştırıldı** — Default SKIP, trend zorunlu, düşük fiyat uyarısı, reason min 10 karakter | `ai_chart_verifier.py` | ✅ |
| 11 | **Review prompt sıkılaştırıldı** — -%10 auto-CLOSE, HOLD için 6 koşul, emin değilsen CLOSE | `ai_chart_verifier.py` | ✅ |
| 12 | **Reason validasyonu** — Boş/kısa reason otomatik SKIP/CLOSE tetikler | `ai_chart_verifier.py` | ✅ |
| 13 | **SL sınırlama** — Max SL %8 ile sınırlı, düşük fiyatlı coinlerde ATR carpanı ayarı | `v7_pa_strategy.py` | ✅ |
| 14 | **Düşük fiyatlı coin filtresi** — $0.01 altı coinlerde pozisyon açılmıyor | `live_v7.py` | ✅ |
| 15 | **Hızlı blacklisting** — 2+ kayıpta anında blacklist, 24h bekleme kaldırıldı | `adaptive_learner.py` | ✅ |
| 16 | **Ardisik kayip korumasi** — 2. kayıpta %50, 3. kayıpta %25 pozisyon boyutu | `live_v7.py` | ✅ |
| 17 | **Sinyal tekrarı engeli** — Açık pozisyonda olan coinlerde yeni sinyal üretilmiyor | `live_v7.py` | ✅ |
| 18 | **Veri tutarsızlığı** — Portfolio ve learning state startup'ta senkronize ediliyor | `live_v7.py` | ✅ |

### Config Yükleme:
- `config_v7.yaml`'daki strateji parametreleri artık her iki bot tarafından okunuyor
- sweep_window=100, max_hold_sweep=7, trend_ema=180, atr_multiplier=0.6, volume_threshold=0.5
- leverage=5, commission_rate=0.00063, max_daily_drawdown_pct=0.05

### RiskEngine Kullanımı:
- Pozisyon açarken drawdown kontrolü yapılıyor
- RR kontrolü yapılıyor (min 5.5)
- Trailing stop her döngüde hesaplanıyor
- Kapanan işlemler self.trades listesine ekleniyor

### MiMo Prompt İyileştirmeleri (29 Haziran 2026):

**Entry Prompt Değişiklikleri:**
- Default davranış: Emin değilsen SKIP (önceki: varsayılan yoktu)
- RSI bandı sıkılaştırıldı: BUY için 30-65 (önceki: <75)
- EMA50 trend zorunluluğu eklendi: Price EMA50 ile aynı yönde olmalı
- Düşük fiyatlı coin uyarısı: $0.01 altında ekstra dikkat
- Pump/dump filtresi: Son 10 mumda >%5 hareket varsa RED
- Reason zorunluluğu: Minimum 10 karakter, boşsa otomatik SKIP

**Review Prompt Değişiklikleri:**
- Otomatik CLOSE kuralları eklendi:
  - PnL < -%10: ALWAYS CLOSE (istisnasız)
  - PnL < -%7 AND held > 24h: CLOSE
  - PnL < -%5 AND ADX < 15: CLOSE
  - RSI < 20 (BUY) veya RSI > 80 (SELL): CLOSE
- HOLD için 6 koşulun TÜMÜ doğru olmalı
- Emin değilsen CLOSE (önceki: HOLD)
- Reason zorunluluğu: Boşsa otomatik CLOSE

**FAIL-OPEN → FAIL-CLOSE:**
- Entry: AI hatasında `approved: True` → `approved: False`
- Review: AI hatasında `action: HOLD` → `action: CLOSE`

**Beklenen Etki:**
- AI hata verdiğinde yeni pozisyon açılmayacak
- Düşük kaliteli sinyaller reddedilecek
- Zararda uzun süre bekleyen pozisyonlar kapatılacak
- Boş reason ile karar alınamayacak

---

## 7. HATALI DOSYALAR LİSTESİ

| Dosya | Satır | Sorun |
|-------|-------|-------|
| `live_v7.py:81` | Config yüklenmeden strateji oluşturuluyor | ✅ DÜZELTİLDİ |
| `live_v5.py:51` | Config yüklenmeden strateji oluşturuluyor | ✅ DÜZELTİLDİ |
| `live_v7.py:357-429` | open_position'da RiskEngine kullanılmıyor | ✅ DÜZELTİLDİ |
| `live_v7.py:435-457` | monitor_positions'da trailing stop yok | ✅ DÜZELTİLDİ |
| `live_v7.py:459-514` | _close_position'da self.trades'a kayıt yok | ✅ DÜZELTİLDİ |
| `live_v7.py:552-554` | Günlük optimizasyon sadece 1 kez çalışıyor | ⏳ DEVAM EDİYOR |
| `live_v5.py:242-258` | _open'da RiskEngine kullanılmıyor | ✅ DÜZELTİLDİ |
| `live_v5.py:260-297` | _close'da trailing stop yok | ✅ DÜZELTİLDİ |
| `src/risk/engine.py:315-368` | Trailing stop hiç çağrılmıyor | ✅ DÜZELTİLDİ |
| `portfolio_state_v7.json` | HMSTR/USDT — API hatası nedeniyle kapatılamayan pozisyon | ✅ SİLİNDİ |
| `live_v7.py:57` | EXCLUDED_SYMBOLS'da HMSTR/USDT yok | ✅ EKLENDİ |
| `ai_chart_verifier.py:208` | FAIL-OPEN — AI hatasında sinyal otomatik onaylanıyordu | ✅ FAIL-CLOSE YAPILDI |
| `ai_chart_verifier.py:841` | FAIL-OPEN review — AI hatasında HOLD dönüyordu | ✅ CLOSE DÖNÜYOR |
| `ai_chart_verifier.py:38-87` | Entry prompt çok gevşek, fazla TRADE onayı | ✅ SIKILAŞTIRILDI |
| `ai_chart_verifier.py:623-666` | Review prompt — HOLD çok kolay, zararda bekliyor | ✅ SIKILAŞTIRILDI |
| `ai_chart_verifier.py:633` | Boş reason kabul ediliyor | ✅ MİN 10 KARAKTER |

---

**Rapor Sonu — MiMoCode tarafından analiz edildi ve düzeltmeler uygulandı**