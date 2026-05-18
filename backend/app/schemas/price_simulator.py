"""
Fiyat simülatörü — kullanıcı bir ürün için satış senaryosu girer:
'Şu fiyata satarsam komisyon + KDV + COGS + hizmet bedeli düştükten sonra ne kalır?'

Müşteri profili (stopaj_rate, KDV mükellefi) otomatik DB'den alınır.
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PriceSimulatorRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sale_price: Decimal = Field(gt=0, description="KDV dahil etiket satış fiyatı (TL)")
    vat_rate: Decimal = Field(default=Decimal("0.20"), ge=0, le=1, description="0.20 = %20")
    commission_rate: Decimal = Field(ge=0, le=1, description="0.12 = %12")
    cogs: Decimal = Field(default=Decimal("0"), ge=0, description="Birim alış maliyeti")
    quantity: int = Field(default=1, ge=1)
    campaign_discount: Decimal = Field(
        default=Decimal("0"), ge=0, description="Kalem başına toplam indirim"
    )
    package_service_fee: Decimal = Field(
        default=Decimal("13.19"), ge=0, description="Trendyol paket hizmet bedeli"
    )
    shipping_cost: Decimal = Field(default=Decimal("0"), ge=0)


class PriceSimulatorResponse(BaseModel):
    # Brüt → net kademeli döküm
    gross_revenue: Decimal       # sale_price × qty
    campaign_discount: Decimal   # düşülen kampanya indirimi
    net_sale: Decimal            # gross - campaign

    # Trendyol kesintileri
    commission: Decimal
    service_fee: Decimal
    shipping_cost: Decimal

    # Vergi
    sale_vat: Decimal

    # Maliyet
    total_cogs: Decimal

    # Stopaj
    stopaj: Decimal

    # Sonuç
    seller_payout: Decimal       # Trendyol'un satıcı hesabına yatırdığı (KDV dahil, COGS hariç)
    net_profit: Decimal          # gerçek net kâr (vergi + COGS dahil)
