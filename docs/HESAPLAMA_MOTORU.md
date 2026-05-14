# Hesaplama Motoru — Matematiksel Spesifikasyon

> Bu doküman net kâr formülünün ne olduğunu **tek otorite** olarak tanımlar. Kod bu dokümanla uyumsuzsa kod yanlıştır.

## 1. Temel kavramlar

### 1.1 Sipariş, paket, kalem hiyerarşisi

```
Order (orderNumber: TY12345)
  └── ShipmentPackage (packageId: P1)
        ├── OrderItem (productId: A, qty: 2)
        └── OrderItem (productId: B, qty: 1)
  └── ShipmentPackage (packageId: P2)
        └── OrderItem (productId: C, qty: 3)
```

Bir sipariş birden fazla pakete bölünebilir. Net kâr **paket bazında** hesaplanır, çünkü paketlerin statüleri farklı olabilir (P1 teslim edildi, P2 iade edildi).

### 1.2 Ana veri tipleri (Decimal kullan)

```python
class OrderItem:
    product_id: int
    barcode: str
    quantity: int
    unit_sale_price: Decimal        # KDV dahil satış fiyatı (Trendyol UI'da görünen)
    vat_rate: Decimal               # 0.10, 0.20 gibi
    commission_rate: Decimal        # kategori bazlı, örn 0.18
    campaign_discount: Decimal      # kalem başına indirim tutarı (varsa)
    return_quantity: int            # iade edilen adet
    cogs: Decimal                   # birim alış maliyeti (müşteri girdisi)

class ShipmentPackage:
    package_id: str
    status: str                     # Delivered, Cancelled, Returned, vs.
    items: list[OrderItem]
    package_service_fee: Decimal    # platform hizmet bedeli (paket başı, KDV dahil)
    shipping_cost: Decimal          # kargo (sipariş başı, satıcı maliyeti)
```

## 2. Net kâr formülü

### 2.1 Kalem bazında (per OrderItem)

```
effective_quantity = quantity - return_quantity

# 1. Brüt gelir (KDV dahil satış)
gross_revenue = unit_sale_price × effective_quantity

# 2. Kampanya indirimi (varsa, ayrı kalemse düşülmüş)
net_sale = gross_revenue - campaign_discount

# 3. Komisyon (Trendyol komisyonu KDV dahil net satış üzerinden)
commission = net_sale × commission_rate

# 4. KDV (satış KDV'si, devlete ödenir)
sale_vat = net_sale × vat_rate / (1 + vat_rate)
# Not: net_sale KDV dahil ise gerçek KDV bu formülle çıkar

# 5. COGS (ürünün gerçek maliyeti)
total_cogs = cogs × effective_quantity

# 6. Kalem net kâr (kargo ve hizmet bedeli hariç, paket bazında dağıtılacak)
item_net = net_sale - commission - sale_vat - total_cogs
```

### 2.2 Paket bazında toplama

```
package_items_net = sum(item.item_net for item in package.items)

# Paket hizmet bedeli ve kargo paket bazında düşülür
package_net_profit = (
    package_items_net 
    - package.package_service_fee
    - package.shipping_cost
)
```

### 2.3 Statüye göre düzeltme

```python
def adjust_for_status(package: ShipmentPackage, raw_profit: Decimal) -> Decimal:
    if package.status == "Cancelled":
        # İptal: hiçbir şey gerçekleşmedi, komisyon ve hizmet bedeli alınmaz
        # Net etki: 0 (ne kazanç ne kayıp)
        return Decimal("0")
    
    if package.status == "Returned":
        # İade: komisyon iade edilir, hizmet bedeli kalır, kargo zarar
        # COGS geri gelir (ürün depoya döner)
        # Net etki: -package_service_fee - shipping_cost
        return -package.package_service_fee - package.shipping_cost
    
    if package.status in ("Delivered", "Shipped", "Invoiced"):
        return raw_profit
    
    if package.status in ("Created", "Picking", "UnSupplied", "UnDelivered"):
        # Henüz tamamlanmamış: tahmini kâr olarak göster, kesin değil
        return raw_profit  # ama UI'da "pending" işareti
```

### 2.4 Sipariş bazında toplama

```
order_net_profit = sum(package_net_profit for package in order.packages)
```

## 3. Kritik detay: Platform hizmet bedeli

Trendyol her paket için sabit bir "platform hizmet bedeli" keser. Kaynak (nekadarsatti.com, Trendyol Akademi):

- **Varsayılan**: 10,99 TL + KDV = **13,188 TL** (paket başına)
- Paket tipi/etiket koşullarına göre değişebilir

MVP'de bunu **sabit 13.19 TL** olarak kabul et. İleride paket tipi haritası eklenecek.

## 4. Kritik detay: Kargo maliyeti

İki farklı senaryo var:

### 4.1 Trendyol anlaşmalı kargo
Trendyol kargo ücretini kendi anlaşmalı tarifesinden keser. Satıcının bilmediği değişken bir tutar. **API'den geliyor mu? Doğrulanması lazım.**

### 4.2 Satıcının kendi kargo anlaşması
Satıcı kendi kargo şirketiyle anlaşmıştır, sabit/değişken ücret öder. **Müşteri panelimizde ayar olarak girer.**

MVP yaklaşımı:
1. Müşteri "varsayılan kargo maliyetim X TL" diye girer
2. İleride desi bazlı tablo eklenir
3. Eğer Trendyol API'sinden cargo_cost geliyorsa onu kullan, gelmiyorsa default'u

## 5. Kampanya simülasyonu

Soru: "Şu üründe %15 indirim yapsam bu ay kârım ne olur?"

```python
def simulate_campaign(
    historical_items: list[OrderItem], 
    discount_pct: Decimal,
    expected_volume_uplift_pct: Decimal = Decimal("0"),
) -> SimulationResult:
    """
    Geçmiş 30 günün siparişlerini al, indirim uygula, kârı yeniden hesapla.
    expected_volume_uplift_pct: indirim ne kadar satışı artıracak tahmini.
    """
    base_profit = sum(calculate_item_profit(item) for item in historical_items)
    
    simulated_items = []
    for item in historical_items:
        new_item = copy(item)
        new_item.unit_sale_price = item.unit_sale_price * (1 - discount_pct)
        new_item.quantity = int(item.quantity * (1 + expected_volume_uplift_pct))
        simulated_items.append(new_item)
    
    simulated_profit = sum(calculate_item_profit(item) for item in simulated_items)
    
    return SimulationResult(
        base_profit=base_profit,
        simulated_profit=simulated_profit,
        delta=simulated_profit - base_profit,
        break_even_volume_uplift=...,  # Hangi hacim artışında başa baş?
    )
```

**Önemli:** İndirim komisyon hesabını da değiştirir, çünkü komisyon yeni (indirimli) fiyat üzerinden hesaplanır.

## 6. KDV mahsuplaşması (opsiyonel, gelişmiş mod)

KOBİ vergi mükellefi ise:
- **Satış KDV'si** (devlete borç)
- **Alış KDV'si** (devletten alacak, COGS içinde)
- **Net KDV** = satış KDV - alış KDV → bu rakam ay sonu ödenir

Bu kâr hesabını şu şekilde etkiler:
- Eğer mükellefse: KDV gider değil, **net KDV** gider
- Eğer değilse: tüm satış KDV'si gider

MVP'de müşteri ayarında "KDV mükellefi misin?" toggle'ı olur. Default: evet (mükellef).

## 7. Stopaj

Trendyol bazı durumlarda satıcıdan stopaj keser. Bu komisyondan sonra net ödemenin bir yüzdesi olarak çalışır.

**MVP'de:** Stopaj manuel ayar olarak `customer.stopaj_rate` field'ı (default 0). Eğer girilirse, paket net kârından düşülür.

## 8. Test fixture'ları için senaryolar

Hesaplama motoru testlerinde MUTLAKA bu senaryolar olmalı:

### Senaryo A: Basit teslim edilen sipariş
- 100 TL satış (KDV %20 dahil)
- %18 komisyon
- 13.19 TL hizmet bedeli
- 0 TL kargo (Trendyol kargo)
- 40 TL COGS
- Statü: Delivered
- Beklenen net kâr: hesapla ve test et

### Senaryo B: Kısmi iade
- 2 adet ürün, 1'i iade
- effective_quantity = 1
- COGS sadece 1 adet için
- Komisyon de 1 adet için

### Senaryo C: Tam iptal
- Sipariş Cancelled
- Net etki: 0

### Senaryo D: Kampanya indirimli
- 100 TL satış, 20 TL indirim
- Komisyon 80 TL üzerinden hesaplanmalı (100 değil)

### Senaryo E: Çoklu paket
- 1 sipariş, 2 paket
- P1 Delivered, P2 Returned
- Toplam kâr = P1.profit + P2.adjusted_profit

### Senaryo F: KDV mükellef olmayan
- Müşteri.kdv_mukellefi = False
- Satış KDV tamamı gider

### Senaryo G: Stopajlı
- customer.stopaj_rate = 0.05
- Net kârdan %5 stopaj düşülmeli

Her senaryo için **input + expected_output** JSON dosyası olarak `tests/fixtures/scenarios/` altında tutulur.
