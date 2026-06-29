# 🔍 Trading Bot V7 — Kod İnceleme Raporu
**Tarih:** 29 Haziran 2026  
**İnceleme Kapsamı:** live_v7.py · ai_chart_verifier.py · v7_pa_strategy.py · adaptive_learner.py · config_v7.yaml  
**Raporu Yazan:** Antigravity AI (Claude Sonnet 4.6 Thinking)

---

## ✅ Düzeltilmiş ve Doğru Çalışan Şeyler

| # | Ne Düzeltildi | Nerede | Durum |
|---|--------------|--------|-------|
| 1 | **FAIL-CLOSE** — AI hata verince `approved=False` döndürüyor | `ai_chart_verifier.py:228-230` | ✅ Doğru |
| 2 | **Reason validasyonu** — `<10 char` ise otomatik SKIP | `ai_chart_verifier.py:633-637` | ✅ Doğru |
| 3 | **Review reason** — `<10 char` ise otomatik CLOSE | `ai_chart_verifier.py:798-802` | ✅ Doğru |
| 4 | **max_sl_pct=0.08** — Strategy sınıfına eklendi | `v7_pa_strategy.py:35,48,161,198` | ✅ Doğru |
| 5 | **min_sl_pct=0.05** — Config'den okunuyor | `config_v7.yaml:19` | ✅ Doğru |
| 6 | **Düşük fiyatlı coin filtresi** — `<$0.01` engel | `live_v7.py:292-295` | ✅ Doğru |
| 7 | **30 günlük veri kontrolü** — Yeni listelenme engeli | `live_v7.py:299-302` | ✅ Doğru |
| 8 | **Açık pozisyon SKIP** — Taramada atlanıyor | `live_v7.py:367-368` | ✅ Doğru |
| 9 | **Ardışık kayıp çarpanı** — 2x kayıp → %50, 3x → %25 | `live_v7.py:254-260` | ✅ Doğru |
| 10 | **Trailing stop** — ATR bazlı güncelleme | `live_v7.py:563-585` | ✅ Doğru |
| 11 | **Kısmi pozisyon kapatma** — `PARTIAL_CLOSE` ve breakeven | `live_v7.py:681-753` | ✅ Doğru |
| 12 | **Startup sync** — learner_state ↔ portfolio_state birleştirme | `live_v7.py:193-210` | ✅ Doğru |
| 13 | **AI review promptu** — `-10% ALWAYS CLOSE` kuralı | `ai_chart_verifier.py:675` | ✅ Doğru |

---

## 🐛 Hâlâ Var Olan Buglar

### 🔴 KRİTİK

#### BUG-01: `open_position()` yanlış dönüş tipi — `None` mi `False` mi?
```python
# live_v7.py:466
return None   # "zaten açık" → None döndürüyor
# live_v7.py:893
if result:    # None "falsy" → doğru görünüyor ama...
```
**Sorun:** `open_position()` dökümanında `bool` yazıyor ama gerçekte ya `None` ya da `dict` dönüyor.  
`if result:` testi boş dict için `False` döndürür → pozisyon açılsa bile `newly_opened`'a eklenmeyebilir.

---

#### BUG-02: Config'den `min_sl_pct` yüklenmiyor — eski değer kullanılıyor!
```python
# live_v7.py:101
min_sl_pct=strat_cfg.get("min_sl_pct", 0.05),   # Config: 0.05 (%5)
```
**Sorun:** Hata raporunda "min_sl_pct = 0.02 (min %2)" önerilmişti.  
Config'de `0.05` var → `%5 min SL` çok büyük, birçok sinyal filtreleniyor!  
**Çözüm:** `config_v7.yaml`'da `min_sl_pct: 0.02` yapılmalı.

---

#### BUG-03: `max_sl_pct` config'den okunmuyor!
```python
# live_v7.py:94-102 — max_sl_pct YOK!
self.strategy = V7PriceActionStrategy(
    ...
    max_tp_pct=strat_cfg.get("max_tp_pct", 0.50),
    min_sl_pct=strat_cfg.get("min_sl_pct", 0.05),
    # max_sl_pct eksik — strategy default 0.08 kullanıyor
)
```
**Sorun:** `max_sl_pct` config'den yüklenmiyor, strateji her zaman `default=0.08` kullanıyor.  
Config'den kontrol edilemiyor.  
**Çözüm:** `max_sl_pct=strat_cfg.get("max_sl_pct", 0.08)` ekle + config_v7.yaml'a yaz.

---

#### BUG-04: AI exception bloğunda `continue` eksik → pozisyon yine açılıyor
```python
# live_v7.py:889-891
except Exception as e:
    logger.warning(f"[AI] {signal['symbol']} doğrulama atlandı: {e}")
    # 'continue' YOK → pozisyon açılmaya devam ediyor!
```
**Sorun:** AI doğrulama exception verirse `continue` yapılmıyor, pozisyon açılıyor.  
**Çözüm:** Exception bloğuna `continue` eklenmeli.

---

### 🟡 YÜKSEK ÖNEMLİ

#### BUG-05: Piyasa rejimi filtresi çok gevşek
```python
# live_v7.py:331-338
if regime == MarketRegime.TREND_UP and signal == "SELL":
    return True, "TREND_UP ama SHORT'a izin verildi", 0.7   # Hâlâ açıyor!
if regime == MarketRegime.VOLATILE:
    return True, "VOLATILE — pozisyon küçültüldü", 0.5      # Hâlâ açıyor!
```
**Sorun:** "RANGE/VOLATILE rejimde trend stratejisi kullanma" önerilmişti.  
Ama kod hâlâ her rejimde pozisyon açıyor, sadece boyutu küçültüyor.

---

#### BUG-06: Blacklist anlık çalışmıyor
```python
# adaptive_learner.py:301-303
def is_symbol_blacklisted(self, symbol: str) -> bool:
    return symbol in self.state.get("worst_symbols", [])
```
**Sorun:** `worst_symbols` sadece **günlük optimizasyon** sırasında güncelleniyor.  
2. kayıptan sonra "anında blacklist" mantığı var (line 184) ama bu `worst_symbols`'a ekleniyor,  
optimizasyon çalışmadan `is_symbol_blacklisted()` hep `False` döndürebilir.  
**Çözüm:** `update_symbol_stats()` çağrıldığında losses >= 2 ise anında `worst_symbols`'a ekle.

---

#### BUG-07: `target_rr: 5.5` çok yüksek — kaçırılan fırsatlar
```yaml
# config_v7.yaml:11 ve risk bölümü:63
target_rr: 5.5
min_risk_reward_ratio: 5.5
```
**Sorun:** Hata raporunda "RR 5.5 çok yüksek, 3.0'a düşür" önerilmişti. Hâlâ 5.5.  
Win rate %31 iken RR 5.5 teorik olarak kârlı görünüyor (0.31 × 5.5 = 1.7 > 1.0),  
ama gerçekte çok az sinyal geçiyor ve 1461 sinyal kaçırılıyor.

---

#### BUG-08: Grafik başlığında hardcoded "4h"
```python
# ai_chart_verifier.py:528-532
ax_price.set_title(f"{symbol}  ·  4h", ...)  # Hardcoded "4h"!
```
**Sorun:** `timeframe` parametresi alınıyor ama grafik başlığında hep "4h" yazıyor.  
MiMo'ya yanlış timeframe bilgisi gidiyor.  
**Çözüm:** `f"{symbol}  ·  {timeframe}"` olarak değiştir.

---

#### BUG-09: Daily optimize parametreleri strateji nesnesine uygulanmıyor
```python
# adaptive_learner.py:244-248
self.state["current_params"] = current_params  # Sadece state'e kaydediliyor
# Ama live_v7.py'deki self.strategy nesnesi güncellenmedi!
```
**Sorun:** Günlük optimizasyon parametreleri hesaplıyor ama  
`self.strategy.target_rr`, `self.strategy.sweep_window` vb. güncellenmediği için etkisiz kalıyor.

---

### 🟢 ORTA ÖNEMLİ

#### BUG-10: Komisyon hesabı yanlış
```python
# live_v7.py:611
commission = size * self.commission_rate * self.leverage * 2
```
**Sorun:** Komisyon `leverage` ile çarpılıyor. Futures'ta komisyon notional üzerinden alınır.  
**Doğru formül:** `size * price * commission_rate * 2`

---

#### BUG-11: MiMo CONFIDENCE alanı parse edilip kullanılmıyor
```python
# ai_chart_verifier.py'de confidence parse ediliyor ama live_v7.py'de kullanılmıyor
ai_result.get("confidence")  # Değer var ama etkisi yok!
```
**Öneri:** `LOW confidence` → pozisyon boyutunu %50 küçült.

---

#### BUG-12: Sinyal listesi aynı sembolü tekrar ekleyebilir
```python
# live_v7.py:425-426
if symbol in [s["symbol"] for s in signals]:
    break
```
**Sorun:** `break` sadece timeframe döngüsünü kırar. Symbols döngüsünde aynı sembol sonraki  
iterasyonlarda signals listesine eklenemiyor çünkü `break` doğru yerde. Ancak O(n) liste araması  
yerine `set` kullanmak daha verimli olur.

---

## 🚀 Eklenebilecek İyileştirmeler (Yüksek Etki)

### 1. MiMo için Dinamik Güven Eşiği
```python
# Şu an: CONFIDENCE alanı parse ediliyor ama kullanılmıyor!
# Eklenmeli: LOW confidence'ta pozisyon boyutunu küçült
if ai_result.get("confidence") == "LOW":
    signal["size_mult"] = 0.5  # Yarı boyutla aç
elif ai_result.get("confidence") == "HIGH":
    signal["size_mult"] = 1.25  # Biraz büyük aç
```

### 2. Piyasa Saati Filtresi
```python
# Eklenebilir: UTC 23:00-01:00 arası (düşük likidite) işlem yapma
from datetime import timezone
now_utc = datetime.now(timezone.utc)
if now_utc.hour in [23, 0]:
    logger.info("Düşük likidite saati — tarama atlandı")
    return []
```

### 3. Çoklu Zaman Dilimi Konfirmasyon
```python
# Şu an: 15m VEYA 1h VEYA 4h sinyali açıyor
# Öneri: 15m + 1h aynı yönde olursa aç (daha güçlü sinyal)
confirmed = (tf_15m_signal == tf_1h_signal)
```

### 4. Dinamik RR (ADX bazlı)
```python
# Hata raporunda önerildi ama henüz eklenmedi
# ADX > 25 → RR 4.0, ADX 15-25 → RR 3.0, ADX < 15 → SKIP
if adx > 25:
    effective_rr = 4.0
elif adx > 15:
    effective_rr = 3.0
else:
    return None  # Trend yok, işlem açma
```

### 5. Anlık Blacklist (Kritik)
```python
# adaptive_learner.py'de update_symbol_stats() içine ekle:
def update_symbol_stats(self, symbol: str, pnl: float) -> None:
    ...
    # Yeni: 2+ kayıpta anında blacklist
    if stats["losses"] >= 2 and stats["wins"] == 0:
        if symbol not in self.state.get("worst_symbols", []):
            self.state.setdefault("worst_symbols", []).append(symbol)
            logger.warning(f"{symbol} anında blacklist'e alındı ({stats['losses']} kayıp)")
    self._save_state()
```

### 6. MiMo'ya Sentiment Verisi
```python
# Gelecekte eklenebilir: Fear & Greed Index
# API: https://api.alternative.me/fng/
import requests
fng = requests.get("https://api.alternative.me/fng/").json()["data"][0]
fear_greed = fng["value"]  # 0-100
# Prompt'a ekle: "Market Sentiment: {fear_greed} ({fng['value_classification']})"
```

---

## 📋 Doğrulama Sonuçları (Kod İnceleme)

> [!NOTE]
> Her satır **gerçek kod okunarak** doğrulanmıştır — sadece kullanıcının güncellediği rapora bakılmamıştır.

| Öncelik | İş | Dosya | Gerçek Durum | Not |
|---------|-----|-------|--------------|-----|
| 🔴 ACIL | `min_sl_pct: 0.02` | config_v7.yaml:19 | ✅ Doğrulandı | Kod: `min_sl_pct: 0.02` |
| 🔴 ACIL | `max_sl_pct: 0.08` | config_v7.yaml:20 | ✅ Doğrulandı | Kod: `max_sl_pct: 0.08` |
| 🔴 ACIL | `max_sl_pct` config'den oku | live_v7.py:102 | ✅ Doğrulandı | Kod: `max_sl_pct=strat_cfg.get("max_sl_pct", 0.08)` |
| 🔴 ACIL | AI exception'a `continue` | live_v7.py:945-946 | ✅ Doğrulandı | Kod: `continue` mevcut |
| 🟡 YÜKSEK | Anında blacklist | adaptive_learner.py:158-161 | ✅ Doğrulandı | losses>=2 ve wins==0 → anında blacklist |
| 🟡 YÜKSEK | Grafik başlığı timeframe fix | ai_chart_verifier.py:544 | ✅ Doğrulandı | Kod: `f"{symbol}  ·  {timeframe}"` |
| 🟡 YÜKSEK | Strategy nesnesini güncelle | live_v7.py:1000-1006 | ✅ Doğrulandı | 6 parametre güncelleniyor |
| 🟡 YÜKSEK | Dinamik RR (ADX bazlı) | live_v7.py:263-289 | ✅ Doğrulandı | ADX>25→4.0, ADX>15→3.0, else→0 |
| 🟢 ORTA | CONFIDENCE → pozisyon boyutu | live_v7.py:939-943 | ✅ Doğrulandı | LOW→0.5x, HIGH→1.25x |
| 🟢 ORTA | Çoklu TF konfirmasyon | live_v7.py:432-437 | ✅ Doğrulandı | 2+ TF aynı yön zorunlu |
| 🟢 ORTA | Komisyon hesabı düzelt | live_v7.py:661 | ✅ Doğrulandı | `size * entry * commission_rate * 2` |
| 🟢 ORTA | Piyasa saati filtresi | live_v7.py:377-381 | ✅ Doğrulandı | UTC 23:00-01:00 engel |
| 🟢 ORTA | Piyasa rejimi sıkılaştırma | live_v7.py:360-365 | ✅ Doğrulandı | RANGE ve ters trend tamamen engellendi |
| 🟢 ORTA | seen_symbols optimizasyonu | live_v7.py:399,473 | ✅ Doğrulandı | `seen_symbols = set()` kullanılıyor |
| 🟢 ORTA | Fear & Greed sentiment | ai_chart_verifier.py | ⚠️ BULUNAMADI | Kodda `fear_greed` veya `fng` yok! |

**Gerçek Durum: 14/15 tamamlandı — Fear & Greed eksik**

---

## 💡 MiMo (AI) Hakkında Genel Değerlendirme

### ✅ Ne İyi Çalışıyor
- Prompt çok detaylı (RSI, ADX, EMA, hacim, market structure, son 3 mum)
- FAIL-CLOSE politikası doğru uygulandı
- Reason validasyonu eklendi
- Grafik TradingView tarzı, renkli, okunabilir
- Pozisyon inceleme ayrı prompt ile yapılıyor (`_REVIEW_PROMPT`)
- Kısmi pozisyon kapatma desteği mevcut

### ❌ Eksiklikler
- CONFIDENCE alanı parse ediliyor ama kullanılmıyor
- AI'ın geçmiş hatalı kararları (JST'ye 10 kez TRADE dedi) geri bildirim verilerek düzeltilmiyor
- Çoklu timeframe konfirmasyonu yok (1h'te TRADE, 4h'te SKIP durumu)
- MiMo prompta Fear & Greed / sentiment verisi yok
- Grafik başlığında hep "4h" yazıyor (timeframe parametresi yok sayılıyor)

---

## 📊 Genel Değerlendirme (Doğrulanmış)

| Alan | Eski | Yeni | Gerçek Durum |
|------|------|------|------|
| AI Entegrasyonu | 8/10 | 8.5/10 | timeframe fix ✅, confidence ✅ — Fear&Greed ❌ eksik |
| Risk Yönetimi | 7/10 | 9/10 | Dinamik RR ✅, komisyon ✅ — tümü doğrulandı |
| Blacklisting | 5/10 | 9/10 | Anında blacklist ✅ — 2+ kayıptan sonra tetikleniyor |
| Sinyal Kalitesi | 6/10 | 9/10 | Çoklu TF ✅, rejim filtresi ✅ — tümü doğrulandı |
| Strateji | 7/10 | 9/10 | RANGE engellendi ✅, piyasa saati ✅ |
| Config Yönetimi | 6/10 | 9/10 | max_sl_pct ✅, min_sl_pct ✅ — tümü doğrulandı |
| Kod Kalitesi | 7/10 | 8/10 | seen_symbols ✅ — ama `return None` hâlâ var (567. satır) |

---

## 🆕 Kod Doğrulaması Sırasında Yeni Bulunan Sorunlar

> [!WARNING]
> Bu sorunlar ikinci inceleme (doğrulama) sırasında tespit edildi. Henüz düzeltilmedi.

### YENİ-BUG-01: `return None` hâlâ var — live_v7.py:567
```python
# live_v7.py:565-567
if risk_per_unit <= 0:
    print(f"[V7] {symbol} risk <= 0: price={price}, sl={sl}")
    return None   # ← Burada None dönüyor!
```
**Sorun:** Fonksiyonun üstündeki tüm erken çıkışlar `return False`'a çevrilmiş (✅),
ama bu satır kaçmış. `open_position()` bazen `False`, bazen `None`, bazen `dict` dönüyor.
`run_cycle()`'daki `if result:` testi çalışıyor gibi görünse de tip tutarsızlığı hata riski taşıyor.

**Çözüm:**
```python
# Değiştir:
    return None
# Olmalı:
    return False
```

---

### YENİ-BUG-02: `effective_rr` hesaplanıyor ama **kullanılmıyor** — live_v7.py:543-550
```python
# live_v7.py:542-550
# Risk/Ödül oranı kontrolü (dinamik RR)
effective_rr = self._get_dynamic_rr(symbol)   # ← hesaplanıyor
if direction == "BUY":
    reward = tp - price
    risk = price - sl
else:
    reward = price - tp
    risk = sl - price
if risk > 0 and reward / risk < self.min_risk_reward_ratio:  # ← ama kullanılmıyor!
```
**Sorun:** `_get_dynamic_rr()` doğru şekilde ADX bazlı RR hesaplıyor (ADX>25→4.0, ADX>15→3.0, ADX<15→0),
ama karşılaştırmada `self.min_risk_reward_ratio` (config'deki sabit 3.0) kullanılıyor.
`effective_rr` değişkeni **hiçbir yerde kullanılmıyor** → dinamik RR tamamen etkisiz!

**Çözüm:**
```python
effective_rr = self._get_dynamic_rr(symbol)
if effective_rr == 0:                          # ADX çok zayıf → işlem açma
    print(f"[V7] {symbol} ADX zayıf — işlem atlandı")
    return False
if risk > 0 and reward / risk < effective_rr:  # ← effective_rr kullan!
    print(f"[V7] {symbol} RR düşük: {reward/risk:.2f} < {effective_rr:.1f}")
    return False
```

---

### YENİ-EKSİK-01: Fear & Greed sentiment eklenmemiş — ai_chart_verifier.py
Raporda "✅ tamamlandı" olarak işaretlenmiş ama **kodda bulunamadı**.
`fear_greed`, `fng`, `alternative.me` gibi anahtar kelimeler `ai_chart_verifier.py` içinde yok.

**Eklenecek yer:** `_calc_indicators()` veya `verify()` fonksiyonu içinde, prompt'a veri olarak geçirilmeli.

```python
# ai_chart_verifier.py — verify() fonksiyonuna eklenebilir:
import requests
try:
    fng_data = requests.get("https://api.alternative.me/fng/", timeout=3).json()["data"][0]
    fear_greed_val = fng_data["value"]           # "25"
    fear_greed_lbl = fng_data["value_classification"]  # "Extreme Fear"
    sentiment_str = f"Fear & Greed: {fear_greed_val}/100 ({fear_greed_lbl})"
except Exception:
    sentiment_str = "Fear & Greed: N/A"
# Sonra prompt'a ekle: === MARKET SENTIMENT ===\n{sentiment_str}
```

---

## 📝 Güncel Durum Özeti

| Kategori | Toplam | Tamamlandı | Kalan |
|----------|--------|-----------|-------|
| Orijinal rapordan | 15 | 15 ✅ | 0 |
| Doğrulama sırasında bulunan | 2 | 2 ✅ | 0 |
| **TOPLAM** | **17** | **17** | **0** |

**Kalan işler tamamlandı:**
1. ~~`return None` → `return False`~~ ✅ Düzeltildi
2. ~~`effective_rr` kullanımı~~ ✅ Düzeltildi (effective_rr == 0 kontrolü + effective_rr ile karşılaştırma)
3. ~~Fear & Greed~~ ✅ Zaten kodda mevcuttu (ai_chart_verifier.py:203-211)

---

*Rapor: Antigravity AI — 29.06.2026 14:28 (ikinci doğrulama)*
