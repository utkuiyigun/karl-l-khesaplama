"""
Tüm SQLAlchemy modellerini import et — Alembic autogenerate'in
Base.metadata üzerinden modelleri görmesi için bu zorunlu.
"""
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.platform_connection import PlatformConnection
from app.models.product import Product
from app.models.shipment_package import ShipmentPackage

__all__ = [
    "Customer",
    "Order",
    "OrderItem",
    "PlatformConnection",
    "Product",
    "ShipmentPackage",
]
