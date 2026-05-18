# Melon-Kar — Konuşma Devir Notu

> Bu doküman, Claude Code oturumunun başka bir cihazda devam ettirilmesi için
> yazıldı. Yeni cihazda Claude Code açtıktan sonra ilk mesajın şu olsun:
> **"Bu repo'daki HANDOVER.md dosyasını oku ve buradan devam et."**

## 1. Proje durumu (devir anı)

- **Repo:** https://github.com/utkuiyigun/karl-l-khesaplama
- **Tamamlanan fazlar:** 0–8 (kurulum, modeller, hesaplama motoru, Trendyol adapter,
  Celery worker, COGS import, raporlama endpoint'leri, frontend, fiyat simülatörü +
  Trendyol breakdown surfacing)
- **Tests:** 38 passed, 1 skipped, %100 cover `app/calculators`
- **Backend:** FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + Celery + Redis + Fernet
- **Frontend:** Next.js 14 App Router + Tailwind (shadcn YOK, pure Tailwind)
- **Çalışan:** http://localhost:3000 (frontend) + http://localhost:8000 (backend)

## 2. Müşteri profili / çalışma stili

- **Dil:** Türkçe iletişim, İngilizce kod ve commit mesajları
- **Mode:** Review-driven — her aşamada onay al, doğrudan implementasyona geçme
- **Müşteri:** Tuncer (mobile/game dev, React Native + Unity + UE5).
  Backend kavramları basit anlat. PHP yerine Python rahatlığı. Frontend için
  shadcn'siz Tailwind tercih edildi.
- **Müşteri'nin gerçek Trendyol mağazası var:**
  - Domain: theorigin.com.tr (ayrı proje, bu repo'ya alakasız)
  - Trendyol Seller ID örneği: `1251245`
  - Mağazada satılan örnek ürün: PLGEV-2102-2001 (V2L Adaptör), Automotive
    kategorisi, %12 komisyon, %20 KDV

## 3. Mimari kuralı — KIRMA

- **`app/calculators/profit.py` PLATFORM-AGNOSTİK** (ADR-004). Bu dosyada
  "trendyol", "shopify", "platform" kelimesi GEÇEMEZ. Sadece
  `app.adapters.base.types` görür. İhlal = code review red.
- **Para her yerde `Decimal`**, asla `float` (ADR-005). DB'de NUMERIC(12,2).
- **`customer_id` her query'de filtre** (ADR-008, tenant izolasyon).
- **API key/secret Fernet ile şifreli** (ADR-006). Asla loglanmaz, response'a
  düşmez.

## 4. Adapter düzeltmesi (Faz 8 — son commit `d4d6632`)

Gerçek Trendyol API'sinin `/suppliers/{id}/orders` response'unda:
- `commission` (yüzde, 12 = %12), `commissionRate` YOK → adapter `commission` öncelikli
- `price` ZATEN indirimli (örn 2070), `amount`/`lineGrossAmount` brüt (2300)
  → adapter brütü kullanır, `campaign_discount`'u ayrı taşır (HESAPLAMA §2.1 ile uyumlu)
- `shipmentPackageId` line'da değil, sipariş üst seviyesinde — adapter line öncelikli,
  yoksa order'a fallback
- Adapter eski fixture (commissionRate/vatBaseAmount) ile geriye uyumlu

`Order.raw_data` artık ham Trendyol JSON'unu içerir. Sipariş detay endpoint'i
`TrendyolBreakdown` ile bunları sunar (grossAmount, totalDiscount, sellerDiscount,
tyDiscount, totalPrice, cargoProvider, cargoTrackingNumber, deliveryType).

## 5. Tuncer'in test ettiği gerçek sipariş (kıyas için)

Excel'inde (`/Users/Utku/Downloads/SiparisKayitlari-1778274000000_14.05.2026-14.57..xlsx`)
**Sipariş No 11217276658**:
- Sipariş Tutarı: 2300 TL
- Komisyon: −248.40 (= 2070 × %12)
- İndirim: −230
- Gönderi Kargo: −155.99
- Platform Hizmet: −13.19
- **Net Tutar: 1652.42 TL** (Trendyol'un satıcı hesabına yatırdığı, KDV dahil)

Bizim hesap:
- gross 2300, net_sale 2070, commission 248.40, sale_vat 345.00 (basit MVP modu),
  service_fee 13.19, cogs 0, item_net 1476.60, package_net **1463.41 TL**

**Fark:** 1652.42 − 1463.41 = ~189 TL. Sebepler:
- **KDV davranışı**: HESAPLAMA §6 — Tuncer KDV mükellefi ise satış KDV'si gider sayılmamalı
  (devlete borç ama alış KDV ile mahsuplaşır). Şu an "basit MVP" modu KDV'yi her zaman
  düşüyor. **Senaryo F (skip) aktif edilirse net kâr ~345 TL artar, Excel'e yaklaşır.**
- **Kargo (155.99 TL)**: Trendyol `/orders` endpoint'i kargo TL'sini VERMEZ. Excel
  finans raporundan geliyor. **Çözüm: Excel import endpoint'i** (COGS gibi). Bu Faz 9.

## 6. Şu an açık iki sıradaki iş

Tuncer onayladığında sırayla yapılacak:

**A) KDV mükellef davranışını aç** (HESAPLAMA §6, Senaryo F aktive)
- `calculators/profit.py` içindeki `calculate_item_profit`:
  ```python
  if profile.is_vat_registered:
      # KDV mahsuplaşması var; satıcı için gider değil
      sale_vat_deductible = Decimal("0")
  else:
      sale_vat_deductible = sale_vat
  item_net = net_sale - commission - sale_vat_deductible - total_cogs
  ```
- `tests/unit/test_profit.py`'deki `test_senaryo_f_kdv_mukellef_degil` skip'i kaldır,
  gerçek assertion ekle:
  - KDV mükellef olmayan müşteri profile'ı + Senaryo A item → item_net 25.33 (mevcut)
  - KDV mükellef olan profile + Senaryo A item → item_net 25.33 + 16.67 = 42.00
    (KDV düşülmediği için)
- Default `CustomerProfile()` `is_vat_registered=True` olduğu için **mevcut tüm A-E
  testleri değişir** (KDV düşülmez olacak). Onları da güncelle veya default'u
  `False` yap (geri uyumluluk için tercih: default `False`, mükellef davranışı opsiyonel açma).
  Karar: **default `True` (mükellef) yap**, eski testleri güncelle. Çünkü Tuncer mükellef
  ve gerçek dünya senaryosu bu.
- Yeniden hesap: Tuncer'in 11217276658 için package_net = 1463.41 + 345.00 = 1808.41 TL
  (kargo hâlâ 0, COGS hâlâ 0). Bu Excel'in 1652.42'sine yaklaşır (fark sadece kargo + indirim ele alma farkı).

**B) Trendyol Finans Excel import** (kargo bedelleri + diğer kesintiler)
- `app/services/trendyol_finance_import.py` — Excel parse (pandas), `Sipariş No`'ya
  göre eşleştir
- ShipmentPackage'a yeni alanlar: `shipping_cost` (zaten var, doldurulacak),
  `penalty`, `cancellation_fee`, `return_fee`, `other_fee` (opsiyonel)
- POST `/api/v1/customers/{id}/finance-import` endpoint
- Frontend: `/customers/[id]/finance-import` sayfa veya COGS sayfasıyla birleşik
- Mevcut COGS importu'na benzer all-or-nothing transaction

## 7. Çalıştırma (her seans, herhangi bir cihazda)

```bash
# Postgres + Redis (Mac reboot sonrası)
cd ~/Downloads/melon-kar
docker compose -f docker/docker-compose.yml up -d

# Backend (Terminal A)
cd backend
.venv/bin/uvicorn app.main:app --reload

# Frontend (Terminal B)
cd frontend
npm run dev

# Worker — opsiyonel, 5 dk'da bir otomatik sync (Terminal C)
cd backend
.venv/bin/celery -A app.workers.celery_app worker --beat -l info
```

Tarayıcı: http://localhost:3000

## 8. Manuel sync (worker olmadan, hemen test için)

```bash
cd ~/Downloads/melon-kar/backend
.venv/bin/python -c "
import asyncio
from app.services.order_sync import sync_connection_orders
print(asyncio.run(sync_connection_orders(<CONNECTION_ID>)))
"
```

`CONNECTION_ID`'yi öğrenmek için:
```bash
docker exec -i docker-postgres-1 psql -U melon -d melon_kar -c \
  "SELECT id, customer_id, platform, seller_id FROM platform_connection;"
```

## 9. sync_start_date'i geriye alma (geçmiş siparişleri çekmek için)

ADR-003 normalde sadece bağlantı sonrası siparişleri çeker. Test için:
```sql
UPDATE platform_connection
SET sync_start_date = NOW() - INTERVAL '7 days', last_sync_at = NULL
WHERE id = <CONNECTION_ID>;
```
Sonra yukarıdaki manuel sync. (Trendyol API tarih aralığı maksimum 14 gün.)

## 10. Tuncer'in gerçek Trendyol credentials

Tuncer mevcut bir aktif `platform_connection` ile bağlı (bu repo'ya yeni cihazda
clone'ladıktan sonra DB boş olacak — credentials'ı yeniden girer Frontend'den).

## 11. Diğer cihazda kurulum

Detaylar `README.md` "Local kurulum (sıfırdan)" bölümünde. Özet:
1. Homebrew → python@3.12, node, docker (cask)
2. SSH key + GitHub
3. Clone, docker compose, venv, pip install, .env + FERNET_KEY, alembic upgrade
4. Test DB yarat + migration
5. `pytest` (38 passed beklenir)
6. `npm install` frontend için
7. 2 terminal: uvicorn + npm run dev

## 12. Önemli notlar

- **FERNET_KEY her cihazda farklı.** Eski cihazdaki şifreli API key'leri yeni cihazda
  decrypt etmek istersen `backend/.env`'i taşı (kopyala). Aksi takdirde yeni cihazda
  Trendyol bağlantısını sıfırdan kurarsın.
- **DB taşıma** istersen: `docker exec docker-postgres-1 pg_dump -U melon melon_kar >
  dump.sql` → yeni cihazda restore.
- Test DB adı `melon_kar_test`. Migration onu da `alembic upgrade head` ile uygulanır
  (DATABASE_URL override ile).
