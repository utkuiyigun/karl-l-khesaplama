# Melon-Kar

Trendyol satıcıları için kârlılık ve finansal analiz aracı.

> **Durum:** Kuruluş aşaması. Mimari kararlar verilmiş, kod yazımı başlıyor.

## Hızlı bakış

- **Ne yapar:** Trendyol mağazasındaki her siparişin gerçek net kârını hesaplar (komisyon + hizmet bedeli + kargo + KDV + COGS dahil).
- **Kim için:** Trendyol satıcıları, başlangıçta proje sahibinin ajans müşterileri.
- **Gelecek:** Shopify desteği (Faz 2).

## Geliştirici için başlangıç

**Önce şu dokümanları sırasıyla oku:**

1. [`PROJE_BRIEF.md`](./PROJE_BRIEF.md) — Projeyi anlamak için ana doküman
2. [`docs/KARARLAR.md`](./docs/KARARLAR.md) — Neden bu seçimler yapıldı (ADR'ler)
3. [`docs/HESAPLAMA_MOTORU.md`](./docs/HESAPLAMA_MOTORU.md) — Net kâr formülünün matematik spec'i
4. [`docs/TRENDYOL_API_NOTLAR.md`](./docs/TRENDYOL_API_NOTLAR.md) — API gotcha'ları

## Local çalıştırma

```bash
# Postgres ve Redis'i başlat
docker compose -f docker/docker-compose.yml up -d

# Backend
cd backend
uv venv
uv pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# Worker (ayrı terminal)
celery -A app.workers.celery_app worker --beat -l info

# Frontend
cd frontend
npm install
npm run dev
```

## Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 16, Celery, Redis
- **Frontend:** Next.js 14, TypeScript, shadcn/ui, Tailwind, Recharts
- **Test:** pytest, pytest-asyncio, factory-boy

## Lisans

Kapalı kaynak. Tüm hakları saklıdır.
