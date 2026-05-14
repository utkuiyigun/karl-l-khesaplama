# Melon-Kar

Trendyol satıcıları için kârlılık ve finansal analiz aracı.

> **Durum:** Backend MVP **tamamlandı**. Frontend henüz yok — API Swagger UI veya curl ile kullanılır.
>
> **Test sonucu:** 38 passed, 1 skipped, 0 failed. `app/calculators` üzerinde %100 coverage.

## Ne yapar

Trendyol mağazasındaki her siparişin **gerçek net kârını** hesaplar:
- Komisyon (kategori bazlı, kampanya indirimli fiyat üzerinden)
- Platform hizmet bedeli (~13.19 TL paket başı)
- Kargo maliyeti
- Satış KDV'si
- Ürün maliyeti (COGS — müşteri CSV ile yükler)
- Stopaj (müşteri tercihine göre)
- Statü düzeltmesi (Cancelled → 0, Returned → fee kaybı)

## Kim için

Proje sahibinin ajans müşterileri (kapalı kullanım, public SaaS değil).

## Mimari özet

```
Trendyol API  →  TrendyolAdapter  →  Order/Package/OrderItem (platform-agnostik)
                                              ↓
                                      Hesaplama Motoru (Decimal, %100 cover)
                                              ↓
                                       Reports endpoint
                                              ↓
                                       Frontend / Swagger UI
```

- **Platform-agnostik hesaplama motoru** (ADR-004): `app/calculators/profit.py` Trendyol kelimesi geçmez.
- **API key Fernet ile şifreli** (ADR-006): DB'de plain text yok.
- **Müşteri başına izole veri** (ADR-008): her query'de `customer_id` filtresi.

## Geliştirici için başlangıç

İlk önce şu dökümanları sırayla oku:

1. [`PROJE_BRIEF.md`](./PROJE_BRIEF.md) — Projeyi anlamak için ana doküman
2. [`docs/KARARLAR.md`](./docs/KARARLAR.md) — Neden bu seçimler yapıldı (ADR'ler)
3. [`docs/HESAPLAMA_MOTORU.md`](./docs/HESAPLAMA_MOTORU.md) — Net kâr formülünün matematik spec'i
4. [`docs/TRENDYOL_API_NOTLAR.md`](./docs/TRENDYOL_API_NOTLAR.md) — API gotcha'ları

## Local kurulum (sıfırdan)

```bash
# 1) Postgres + Redis container'ları (her makine reboot sonrası tekrar)
docker compose -f docker/docker-compose.yml up -d

# 2) Backend ortamı
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 3) .env dosyasını oluştur (root dizinde .env.example var)
cd ..
cp .env.example backend/.env
# FERNET_KEY'i üret ve .env'e yapıştır:
backend/.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 4) Test DB'yi yarat (testler için; dev DB zaten docker-compose ile yaratıldı)
docker exec -i docker-postgres-1 psql -U melon -d melon_kar -c "CREATE DATABASE melon_kar_test;"

# 5) Migration'ları uygula (her iki DB için)
cd backend
.venv/bin/alembic upgrade head
DATABASE_URL="postgresql+asyncpg://melon:melon_dev@localhost:5432/melon_kar_test" \
  .venv/bin/alembic upgrade head

# 6) Test suite
.venv/bin/pytest

# 7) API'yi başlat
.venv/bin/uvicorn app.main:app --reload
# → http://127.0.0.1:8000/docs (Swagger UI)

# 8) Worker (ayrı terminal — Trendyol polling için)
.venv/bin/celery -A app.workers.celery_app worker --beat -l info
```

## API endpoint'leri (özet)

Detay için `http://127.0.0.1:8000/docs` Swagger UI'a bak.

| Method | Path | Açıklama |
|---|---|---|
| GET    | `/health` | Healthcheck |
| POST   | `/api/v1/customers` | Müşteri oluştur |
| GET    | `/api/v1/customers` | Müşteri listesi (limit/offset) |
| GET    | `/api/v1/customers/{id}` | Müşteri detayı |
| PATCH  | `/api/v1/customers/{id}` | Müşteri güncelle (stopaj_rate vs.) |
| POST   | `/api/v1/customers/{id}/connections` | Trendyol bağlantısı kur (API key Fernet ile şifrelenir) |
| GET    | `/api/v1/customers/{id}/connections` | Bağlantı listesi |
| PATCH  | `/api/v1/customers/{id}/connections/{cid}` | Key rotation veya aktif/pasif |
| DELETE | `/api/v1/customers/{id}/connections/{cid}` | Bağlantıyı sil |
| GET    | `/api/v1/customers/{id}/cogs/template` | Boş CSV şablonu indir |
| POST   | `/api/v1/customers/{id}/cogs` | COGS Excel/CSV yükle |
| GET    | `/api/v1/customers/{id}/orders` | Sipariş listesi + her satırda net kâr |
| GET    | `/api/v1/customers/{id}/orders/{oid}` | Sipariş detayı + paket bazlı breakdown |
| GET    | `/api/v1/customers/{id}/products/profitability` | Ürün bazlı kârlılık raporu |
| POST   | `/api/v1/customers/{id}/simulations` | Kampanya simülasyonu (% indirim → tahmini kâr) |

## Manuel uçtan uca test akışı

Gerçek Trendyol verisi olmadan da test edebilirsin: aşağıdaki adımlar Swagger UI'dan veya curl ile çalışır.

```bash
# 1) Müşteri oluştur
curl -X POST http://127.0.0.1:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"email":"deneme@test.com","name":"Deneme","stopaj_rate":"0"}'

# 2) Bağlantı kur (gerçek Trendyol API key/secret + sellerId koy)
curl -X POST http://127.0.0.1:8000/api/v1/customers/1/connections \
  -H "Content-Type: application/json" \
  -d '{
    "platform":"trendyol",
    "seller_id":"YOUR_SELLER_ID",
    "api_key":"YOUR_TRENDYOL_API_KEY",
    "api_secret":"YOUR_TRENDYOL_API_SECRET"
  }'

# 3) COGS template indir
curl http://127.0.0.1:8000/api/v1/customers/1/cogs/template -o cogs.csv
# cogs.csv'i Excel'de aç, doldur, kaydet

# 4) COGS yükle
curl -X POST http://127.0.0.1:8000/api/v1/customers/1/cogs \
  -F "file=@cogs.csv"

# 5) Worker'ı bekle (5 dakika içinde otomatik sync tetiklenir)
#    Veya manuel tetikleme:
cd backend && .venv/bin/python -c "
import asyncio
from app.services.order_sync import sync_connection_orders
print(asyncio.run(sync_connection_orders(1)))
"

# 6) Raporları gör
curl http://127.0.0.1:8000/api/v1/customers/1/orders | python3 -m json.tool
curl http://127.0.0.1:8000/api/v1/customers/1/products/profitability | python3 -m json.tool

# 7) Kampanya simülasyonu (örn. %15 indirim, %10 hacim artışı varsayımı)
curl -X POST http://127.0.0.1:8000/api/v1/customers/1/simulations \
  -H "Content-Type: application/json" \
  -d '{"discount_pct":"0.15","volume_uplift_pct":"0.10"}'
```

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 16, Celery, Redis, Fernet
- **Test:** pytest, pytest-asyncio, httpx ASGI transport, monkeypatch ile mock'lar
- **Frontend:** Henüz yazılmadı (Faz 7'ye bırakıldı)

## Test sayıları

```
tests/integration/test_cogs_import.py          8 passed
tests/integration/test_connections_encryption.py  4 passed
tests/integration/test_order_sync.py           4 passed
tests/integration/test_reports.py              6 passed
tests/integration/test_trendyol_adapter.py     5 passed
tests/unit/test_profit.py                     11 passed, 1 skipped

Total:  38 passed, 1 skipped
Coverage on app/calculators: 100%
```

## Lisans

Kapalı kaynak. Tüm hakları saklıdır.
