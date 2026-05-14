# Mimari Kararlar Logu (ADR)

> Verilen her büyük kararın gerekçesi burada. Bir karar değiştirilecekse önce burası tartışılır.

## ADR-001: MVP'de sadece Trendyol, Shopify Faz 2
**Tarih:** 2026-05-14  
**Karar:** İlk versiyonda sadece Trendyol adaptörü yazılır. Shopify adaptörü Faz 2'ye bırakılır.

**Neden:**
- Mevcut test müşterileri Trendyol'da
- İki API paralel geliştirmek tek geliştiriciyi yavaşlatır (2x değil, 3x)
- Trendyol'da hesaplama formülü bile karmaşık, Shopify'ı eklemek zihinsel yük

**Sonuç:** Veri modeli ve adaptör interface'i Shopify'ı kaldıracak şekilde tasarlanır ama implementasyon edilmez.

---

## ADR-002: Webhook yerine polling
**Tarih:** 2026-05-14  
**Karar:** Trendyol siparişleri Celery beat ile her 5 dakikada bir polling ile çekilir.

**Neden:**
- Trendyol webhook desteği vermez (resmi dokümantasyonda yok)
- Polling, Celery + Redis kurulumunu zorunlu kılar
- 5 dk gecikme finansal raporlama için kabul edilebilir (real-time değil zaten gerekli değil)

---

## ADR-003: Sadece bugünden ileriye veri çek
**Tarih:** 2026-05-14  
**Karar:** Geçmiş siparişler API'den çekilmez. Müşteri bağlandığı andan itibaren veri toplanır.

**Neden:**
- Geçmiş komisyon yapısı değişmiş olabilir, tarihsel doğruluk imkânsız
- Geçmiş COGS bilinmez (müşteri o zamanki maliyetleri girmeyebilir)
- Daha temiz ürün hikâyesi: "bugünden itibaren net kârını takip et"
- Geliştirme süresini ~%30 kısaltır

**Sonuç:** Migration job, geçmiş veri parser yok. PlatformConnection oluşturulduğu anki tarih `sync_start_date` olarak kaydedilir.

---

## ADR-004: Hesaplama motoru platform-bağımsız
**Tarih:** 2026-05-14  
**Karar:** `calculators/profit.py` Trendyol'u veya Shopify'ı asla bilmez. Sadece kendi iç `Order` modelini görür.

**Neden:**
- Mantığın iki yere kopyalanmasını engeller
- Test edilebilirlik (mock platform fixture'ları)
- Yeni platform eklemek = sadece yeni adaptör yazmak (Çıkma + Yeniden yazma yok)

**İhlal halinde:** Code review'da reddedilir. `if platform == "..."` hesaplama motorunda olamaz.

---

## ADR-005: Para Decimal, asla float
**Tarih:** 2026-05-14  
**Karar:** Tüm para alanları Python tarafında `Decimal`, DB'de `NUMERIC(12, 2)`, JSON'da string.

**Neden:**
- `0.1 + 0.2 != 0.3` (IEEE 754)
- Finansal hesapta float kullanmak bug değil, ihmaldir
- Pydantic v2 Decimal'ı doğal destekler

---

## ADR-006: Müşteri API key'leri Fernet ile şifreli
**Tarih:** 2026-05-14  
**Karar:** Trendyol API key/secret DB'de Fernet (symmetric encryption) ile şifrelenir.

**Neden:**
- Plain text saklamak yasal sorumluluk
- DB dump çalınırsa bile key'ler kullanılamaz
- Fernet basit, Python stdlib uyumlu, AES-128 + HMAC

**Master key:** `.env`'de `FERNET_KEY`. Prod'da secret manager'dan gelir.

---

## ADR-007: COGS Excel/CSV ile toplu yükleme
**Tarih:** 2026-05-14  
**Karar:** Müşteri ürün maliyetlerini manuel girmez, CSV/Excel template'i indirip doldurup yükler.

**Neden:**
- Trendyol'da 100-1000+ ürün olabilir, tek tek giriş ölür
- Ajans olarak proje sahibi de müşteri adına yükleyebilir
- pandas ile validation kolay

**Sonuç:** `services/cogs_import.py` modülü, template indirme endpoint'i, upload endpoint'i.

---

## ADR-008: Multi-tenant'ın basit hali — row-level filtering
**Tarih:** 2026-05-14  
**Karar:** Tek DB, her tablo `customer_id` kolonu, her query'de filtre.

**Neden:**
- Müşteri başına ayrı DB schema overkill (ajans modeli, ~50 müşteri max)
- Row-level security PostgreSQL'de var ama karmaşık, ileride eklenir
- Kod tarafında SQLAlchemy session helper ile her query'e `customer_id` filtresi enforce edilir

**Risk:** Geliştirici unutursa veri sızar. Bu yüzden CI'da static analiz check'i: query'de customer_id var mı?

---

## ADR-009: NextAuth.js + magic link
**Tarih:** 2026-05-14  
**Karar:** Şifre yönetmiyoruz. Müşteri email'ine link gelir, tıklar, giriş yapar.

**Neden:**
- Ajans müşterileri, sayı az, davet flow'u doğal
- Şifre reset, lockout, MFA hepsi karmaşık, gerekmez
- Phishing açısından da daha iyi

---

## ADR-010: Frontend ayrı deploy, monorepo değil — şimdilik
**Tarih:** 2026-05-14  
**Karar:** Backend ve frontend ayrı klasörlerde, ayrı CI/CD, monorepo tooling yok (turbo, nx).

**Neden:**
- Tek geliştirici, monorepo karmaşası getirir
- API contract'ı OpenAPI ile paylaşılır
- İleride monorepo'ya çevirmek zor değil
