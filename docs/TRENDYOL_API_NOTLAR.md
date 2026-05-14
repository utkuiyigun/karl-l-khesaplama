# Trendyol API — Pratik Notlar

> Bu doküman geliştirme sırasında karşılaşılan gerçek durumları kaydeder. Yeni keşfedildiğinde buraya ekle.

## 1. Resmi kaynaklar

- Ana doc: https://developers.trendyol.com/
- Authorization: https://developers.trendyol.com/en/docs/authorization
- Türkçe entegrasyon: https://developers.trendyol.com/docs/marketplace
- Stage env: IP whitelisting şart, mail ile başvuru

## 2. Auth

- **Yöntem:** HTTP Basic Auth
- **Username:** API Key (Trendyol partner panelinden)
- **Password:** API Secret
- **Header:** `Authorization: Basic base64(apiKey:apiSecret)`
- **User-Agent ZORUNLU:** `{sellerId} - SelfIntegration` veya `{sellerId} - {IntegratorName}` (User-Agent yoksa 403)
- Bizim case'imizde User-Agent: `{seller_id} - MelonKar`

## 3. Base URL

- **Prod:** `https://api.trendyol.com/sapigw/`
- **Stage:** Farklı, IP whitelist ile

## 4. Önemli endpoint'ler (sipariş için)

### GET /suppliers/{supplierId}/orders
Siparişleri listele. Query parametreler:

| Param | Tip | Açıklama | Limit |
|---|---|---|---|
| startDate | timestamp (ms) | Başlangıç tarihi | - |
| endDate | timestamp (ms) | Bitiş tarihi | Maks 14 gün aralık |
| page | int | Sayfa numarası | 0-indexed |
| size | int | Sayfa boyutu | Maks 200 |
| orderNumber | string | Tek sipariş çek | - |
| status | string | Statü filtresi | Bkz. status değerleri |
| orderByField | string | Sıralama alanı | `CreatedDate` veya `PackageLastModifiedDate` |
| orderByDirection | string | Sıralama yönü | `ASC` / `DESC` |

**Bizim için doğru polling stratejisi:**
```
orderByField = PackageLastModifiedDate
orderByDirection = DESC
startDate = last_sync_timestamp - 1 hour (overlap buffer)
endDate = now
```

`PackageLastModifiedDate` kullanmak şart, çünkü statü değişimi (Returned vs.) bunu update eder.

### GET /suppliers/{supplierId}/products
Ürün listesi. COGS yüklemesi için barkod eşleştirme yapacağız.

## 5. Sipariş statüleri

| Statü | Anlamı | Kâr hesabına etkisi |
|---|---|---|
| Created | Yeni oluştu | Pending — tahmini |
| Picking | Hazırlanıyor | Pending |
| Invoiced | Faturalandı | Realized (büyük ihtimalle gidecek) |
| Shipped | Kargolandı | Realized |
| Delivered | Teslim edildi | Tam realized |
| Cancelled | İptal | Etki yok (0) |
| UnDelivered | Teslim edilemedi | Pending — iadeye dönebilir |
| Returned | İade edildi | Negatif (hizmet bedeli + kargo zararı) |
| Repack | Yeniden paketleme | Pending |
| UnSupplied | Temin edilemedi | Etki yok ama bizim açımızdan satılamadı |

## 6. Bilinmeyen ve doğrulanması gerekenler

> Aşağıdaki sorulara cevap, gerçek API response örnekleri alındıkça bulunacak. Her cevap geldikçe burayı güncelle.

- [ ] `commissionFee` her kalemde mi geliyor, sipariş bazında mı?
- [ ] Platform hizmet bedeli (~13.19 TL) API response'unda yer alıyor mu, yoksa hesaplamamız mı gerekecek?
- [ ] Kargo maliyeti API'de var mı? Hangi alanda?
- [ ] Stage ortamda IP whitelist hızı (1 gün mü, 1 hafta mı)?
- [ ] Rate limit gerçek sınırı nedir? (429 alana kadar dene)
- [ ] Kampanya indirimi `discount` field'ında mı yoksa `lineDiscount`?
- [ ] İade durumunda komisyon iade tutarı response'da ayrı bir kalem mi?

**Aksiyon:** Müşterilerden bir test API key alındığında bu soruları gerçek response'larla cevapla, fixture'ları kaydet.

## 7. Hata yönetimi

| HTTP code | Anlamı | Aksiyon |
|---|---|---|
| 200 | OK | - |
| 400 | Bad request | Log + alert, retry yok |
| 401 | Yanlış auth | Müşteriye "API key'iniz hatalı" göster |
| 403 | User-Agent eksik veya IP block | Header'ı kontrol et |
| 429 | Rate limit | Exponential backoff (1, 2, 4, 8, 16 sn) |
| 5xx | Trendyol sorunu | Retry, alert if persistent |

## 8. Sync stratejisi (her müşteri için)

```python
async def sync_orders_for_customer(customer_id: int):
    conn = get_connection(customer_id)
    last_sync = conn.last_sync_at or conn.created_at
    
    # Overlap buffer: aynı kayıt iki kez güncellenebilir, idempotent yap
    start = last_sync - timedelta(hours=1)
    end = now()
    
    # Chunk'la, max 14 günlük pencereler
    for chunk_start, chunk_end in chunk_date_range(start, end, days=13):
        page = 0
        while True:
            resp = await client.list_orders(
                supplier_id=conn.seller_id,
                start_date=chunk_start,
                end_date=chunk_end,
                page=page,
                size=200,
                order_by_field="PackageLastModifiedDate",
                order_by_direction="DESC",
            )
            
            await save_orders(customer_id, resp.content)
            
            if page >= resp.totalPages - 1:
                break
            page += 1
    
    conn.last_sync_at = end
    await session.commit()
```

## 9. Idempotency

Aynı sipariş tekrar çekildiğinde DB'de duplicate olmamalı:

```sql
CREATE UNIQUE INDEX ix_orders_platform_external 
ON orders (platform_connection_id, external_id);
```

Upsert için `INSERT ... ON CONFLICT DO UPDATE`.
