# Melon-Kar — Proje Brief'i

> **Claude Code için**: Bu dokümanı tamamen oku ve anladığını teyit et. Sonra `KARARLAR.md` ve `HESAPLAMA_MOTORU.md` dosyalarını oku. Bu üç doküman projenin tüm bağlamını içerir. Kod yazmaya başlamadan önce planını sun.

## 1. Proje nedir

Pazaryeri satıcıları için **kârlılık ve finansal analiz aracı**. Trendyol referans alındı (Melontik benzeri). MVP'de **sadece Trendyol** desteklenecek; mimari Shopify'ı da kaldıracak şekilde tasarlanır ama Shopify adaptörü Faz 2'ye bırakıldı.

Hedef kullanıcı: Proje sahibinin ajans müşterileri (kapalı kullanım, public SaaS değil).

## 2. Çözülen problem

Trendyol satıcısı "bu siparişte ne kadar kazandım?" sorusuna doğru cevap veremiyor. Çünkü Trendyol API'si:

- **Komisyon tutarını** sınırlı detayda veriyor
- **Platform hizmet bedelini** ayrı kalem olarak vermez (paket başı kesilen ~13 TL)
- **Kargo maliyetini** satıcı kargo modeline göre değişken bırakır
- **Ürün maliyetini (COGS)** zaten bilmez — bu satıcının kendi verisidir
- **Reklam harcamasını** ayrı API'de tutar
- **KDV mahsuplaşmasını** hesaplamaz
- **Stopaj** hiç yoktur

Sonuç: satıcı "gelir geldi" görür ama net kârı bilmez. Bizim ürünümüz **bu boşluğu doldurur**.

## 3. MVP kapsamı (sadece şunlar)

### Yapılacaklar
- Trendyol API bağlantısı (müşteri kendi API key'ini girer)
- Siparişleri **bugünden ileriye** doğru otomatik çekme (geçmiş veri YOK)
- Ürün maliyeti (COGS) için **Excel/CSV toplu yükleme**
- Sipariş bazlı net kâr hesabı
- Ürün bazlı kârlılık raporu
- Kampanya/indirim simülasyonu ("eğer %20 indirim yapsam kâr ne olur?")
- Basit dashboard (sipariş listesi, ürün tablosu)
- Müşteri başına izole veri (multi-tenant'ın basit hali)

### YAPILMAYACAKLAR (kapsam dışı)
- Geçmiş siparişlerin migration'ı (sadece bugünden ileriye)
- Otomatik fiyatlandırma (Faz 2)
- Reklam ROI analizi (Faz 2)
- Ödeme mutabakatı (Faz 2)
- Shopify adaptörü (Faz 2 — sadece veri modelinde hazırlık)
- Mobile app (web yeter)
- Public SaaS özellikleri (signup flow, billing, trial vs.)

## 4. Tech stack — neden bu seçimler

| Katman | Seçim | Gerekçe |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Proje sahibinin deneyimi var, async I/O Trendyol API için ideal |
| ORM | SQLAlchemy 2.0 (async) + Alembic | Migration disiplini şart, finansal veri schema'sı evrim geçirecek |
| DB | PostgreSQL 16 | ACID, JSON kolon, numeric tip, finansal veri için tek doğru seçim |
| Cache/Queue | Redis 7 + Celery | Trendyol polling'i background job olmak ZORUNDA (webhook yok) |
| HTTP client | httpx (async) | requests'ten daha modern, native async |
| Validation | Pydantic v2 | FastAPI standardı |
| Frontend | Next.js 14 (App Router) + TypeScript | Modern React, server components |
| UI | shadcn/ui + Tailwind + Recharts | Kontrol bizde, kütüphane bağımlılığı az |
| Auth | NextAuth.js (email magic link) | Ajans müşterileri için davet flow'u, password yönetimine girmiyoruz |
| Şifreleme | cryptography.Fernet | Müşteri API key'leri DB'de plain text OLAMAZ |
| Test | pytest + pytest-asyncio + factory-boy | Hesaplama motoru için %100 coverage zorunlu |
| Container | Docker + docker-compose | Local dev ve prod aynı ortam |

## 5. Mimari prensipler — bunlardan sapma

### 5.1 Platform-bağımsız hesaplama motoru
**Bu projenin EN ÖNEMLİ kuralı.** Hesaplama motoru asla Trendyol veya Shopify'ı bilmemeli. Sadece kendi iç veri modelimizi (`Order`, `OrderItem`, `Cost`) görür ve net kâr hesaplar.

Trendyol adaptörü ham Trendyol JSON'unu alıp bizim iç modele dönüştürür. Shopify adaptörü de aynı şeyi Shopify JSON'u için yapar. Hesaplama motoru ikisini ayırt etmez.

Bu kural ihlal edilirse (örn. hesaplama motoruna `if platform == "trendyol"` yazılırsa) **kod red edilir, baştan yazılır**.

### 5.2 Test-first hesaplama motoru
Hesaplama motoru kodunun **her satırı** için unit test yazılır. Yanlış kâr hesabı = müşteri kaybı. Şu test örnekleriyle başla:

- "100 TL satış, %20 komisyon, 13.19 TL hizmet, 30 TL COGS → net kâr ?"
- "İade edilen kalem, kârı sıfırlamalı mı eksiye düşürmeli mi?"
- "Kampanya indirimi varsa komisyon hangi tutar üzerinden hesaplanır?"

Test fixture'ları `backend/tests/fixtures/` altında saklanır. Bunlar gerçek Trendyol API response örneklerinden türetilir (PII temizlenmiş).

### 5.3 Para hep `Decimal`, asla `float`
Finansal hesapta float = bug. Tüm para alanları `Decimal` (Python tarafında) ve `NUMERIC(12, 2)` (PostgreSQL tarafında). JSON serialization'da string'e çevrilir.

### 5.4 Müşteri veri izolasyonu
Her query'de `customer_id` filtresi olmak ZORUNDA. SQLAlchemy'de row-level filtering için custom session helper kullan. Yanlışlıkla başka müşterinin verisi sızarsa = yasal sorun + ürün ölür.

### 5.5 API key'ler asla loglanmaz
Müşterinin Trendyol API key'i logger'a düşmemeli, error message'a düşmemeli, Sentry'e düşmemeli. Fernet ile şifreli saklan, decrypt sadece kullanırken yapılır, kullanım sonrası değişken silinir.

## 6. Trendyol API gotcha'ları (önemli!)

### 6.1 Webhook yok
Trendyol "yeni sipariş geldi" diye bildirim göndermez. **Polling zorunlu.** Her müşteri için ayrı Celery beat scheduler, 5 dakikada bir son güncellenen siparişleri çeker.

### 6.2 Tarih aralığı limiti: 14 gün
Bir API çağrısında en fazla 2 haftalık veri çekilebilir. Daha geniş aralık için chunk'lama yap.

### 6.3 Page size limiti: 200
Pagination zorunlu. Async paralel sayfa çekimi yapılabilir ama rate limit'e dikkat.

### 6.4 Rate limit (resmi olarak yazılı değil ama var)
Hata aldığımızda exponential backoff ile retry. Tenacity kütüphanesi kullan.

### 6.5 Stage vs prod ortam ayrı
Stage'e erişim için IP whitelisting şart. Geliştirme aşamasında bu mümkünse müşteri panelinden alınır, değilse direkt prod ile mock test fixture'ları kullanılır.

### 6.6 Sipariş paketleri (shipmentPackage)
Bir sipariş (orderNumber) birden fazla pakete bölünebilir (shipmentPackageId). Her paketin kendi statüsü vardır. Net kâr hesabı **paket bazında** yapılmalı.

### 6.7 Statüler
`Created, Picking, Invoiced, Shipped, Cancelled, Delivered, UnDelivered, Returned, Repack, UnSupplied`. Her statüde komisyon hesabı farklı davranır:

- `Cancelled` → komisyon 0
- `Returned` → komisyon iade edilmiş, kâra geri eklenir ama COGS düşer (ürün döndü, satılmadı)
- `Delivered` → tam kâr realized

## 7. Klasör yapısı

```
backend/
  app/
    main.py                    # FastAPI app entry
    core/
      config.py                # Pydantic settings
      security.py              # Fernet encryption helpers
      logging.py               # Structured logging
    db/
      session.py               # Async SQLAlchemy session
      base.py                  # Declarative base
    models/                    # SQLAlchemy ORM models
      customer.py
      platform_connection.py
      product.py
      order.py
      order_item.py
    schemas/                   # Pydantic schemas (request/response)
    adapters/
      base/
        adapter.py             # Abstract MarketplaceAdapter
        types.py               # Common dataclasses (Order, OrderItem)
      trendyol/
        client.py              # httpx async client
        adapter.py             # Trendyol -> internal model converter
        types.py               # Trendyol-specific types
      shopify/                 # Faz 2 - şimdilik sadece skeleton
    calculators/
      profit.py                # Net kâr hesaplama motoru (platform-bağımsız!)
      campaign.py              # Kampanya simülasyonu
      vat.py                   # KDV mahsuplaşma (opsiyonel)
    services/
      cogs_import.py           # CSV/Excel COGS yükleme
      order_sync.py            # Adaptörden veri çekme orkestrasyon
    workers/
      celery_app.py
      tasks.py                 # @app.task'lar
      schedules.py             # Celery Beat
    api/v1/
      auth.py
      customers.py
      connections.py           # Platform bağlantısı yönetimi
      orders.py
      products.py
      reports.py
      simulations.py           # Kampanya simülasyon endpoint'i
  tests/
    unit/                      # Saf fonksiyon testleri (calculators)
    integration/               # DB ile testler
    fixtures/                  # Trendyol API response örnekleri
  alembic/                     # Migration dosyaları
  pyproject.toml
  Dockerfile
frontend/
  (Next.js 14 — başlangıçta minimal)
docker/
  docker-compose.yml           # Postgres + Redis + backend + worker
docs/
  KARARLAR.md
  HESAPLAMA_MOTORU.md
  TRENDYOL_API_NOTLAR.md
.env.example
README.md
```

## 8. Geliştirme sırası — kesin sırayla

Claude Code şu sırayla ilerlemeli:

### Faz 0: Setup (1 gün)
1. pyproject.toml, dependencies
2. docker-compose.yml (postgres + redis)
3. FastAPI iskelet, healthcheck endpoint
4. Alembic init
5. Core: config, logging, security (Fernet wrapper)

### Faz 1: Veri modeli + temel CRUD (2-3 gün)
1. SQLAlchemy modelleri
2. İlk migration
3. Pydantic schemas
4. Customer ve PlatformConnection için CRUD endpoint
5. **Burada test yaz: PlatformConnection oluştururken API key'in şifreli kaydedildiğini test et**

### Faz 2: Hesaplama motoru (en kritik, 3-4 gün)
**Önce test fixture'ları:** `backend/tests/fixtures/trendyol_orders/` altına 10-15 gerçekçi sipariş JSON'u koy (proje sahibinden alınacak veya gerçek anonim örneklerden).

1. `Order`, `OrderItem`, `Cost`, `Revenue` dataclass'ları (`adapters/base/types.py`)
2. `calculators/profit.py`: `calculate_net_profit(order: Order) -> ProfitResult`
3. **Önce TESTLERİ YAZ**, sonra implementasyonu yaz (TDD)
4. KDV, kampanya, iade senaryolarını ayrı ayrı test et
5. Hedef: %100 line coverage, motorun her dalı test edilmiş olmalı

### Faz 3: Trendyol adaptörü (2-3 gün)
1. `adapters/trendyol/client.py`: httpx async client, retry, rate limit handling
2. `adapters/trendyol/adapter.py`: ham JSON → iç model
3. Integration test: mock httpx ile Trendyol response'unu iç modele dönüştürmeyi test et
4. **NOT:** Adaptör hesaplama yapmaz, sadece dönüştürür

### Faz 4: Worker + senkronizasyon (2 gün)
1. Celery setup
2. `tasks.sync_orders_for_customer(customer_id)`
3. Celery Beat: her aktif müşteri için 5 dakikada bir
4. Hata yönetimi, retry, alert

### Faz 5: COGS import (1-2 gün)
1. CSV/Excel upload endpoint
2. pandas ile parsing
3. Validation (barkod var mı, sayısal mı, vs.)
4. Bulk update

### Faz 6: Raporlama endpoint'leri (2 gün)
1. Sipariş listesi (filtre + pagination)
2. Ürün kârlılık tablosu
3. Kampanya simülasyon endpoint'i
4. Excel export

### Faz 7: Frontend (sonra — backend stabil olduktan sonra)

## 9. Çalışma modu — Claude Code için talimatlar

- **Review-driven mode** kullan (proje sahibi bunu tercih ediyor)
- Her faz bittiğinde **checkpoint** oluştur, küçük adımlarda ilerle
- Test yazmadan kod yazma. Hesaplama motorunda **kesinlikle test-first**.
- Belirsizlik varsa varsayım yapma, sor.
- Türkçe yorum yazabilirsin ama değişken/fonksiyon adları İngilizce.
- Commit mesajları İngilizce, conventional commits formatı.
- Her major işten sonra `docs/CHANGELOG.md` güncelle.

## 10. Bilinen riskler

| Risk | Etki | Azaltma |
|---|---|---|
| Trendyol API rate limit'i bilmiyoruz | Polling tıkanır | Exponential backoff + monitoring |
| Komisyon yapısı kategoriye göre değişiyor | Yanlış hesap | Komisyon oranları DB'de tablo olarak tut, müşteri override edebilsin |
| Hizmet bedeli paket tipine göre değişir | ~5-15 TL hata | İlk versiyonda sabit, sonra paket tipine göre haritala |
| KDV mahsuplaşması karmaşık | Yanlış vergi hesabı | MVP'de "basit mod" ver, gelişmiş ayar olarak işaretle |
| Müşteri API key'i sızdırırsa | Mağaza hacklenebilir | Fernet şifreleme + key rotation desteği |
| Para birimi tutarsızlığı | Hesap bozulur | Tüm para `Decimal`, tüm tutarlar TL, KDV oranı kalemde |
