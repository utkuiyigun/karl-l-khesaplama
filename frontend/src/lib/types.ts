// Backend API ile uyumlu TypeScript tipleri.
// Sayısal alanlar Decimal serialize edildiği için string olarak gelir.

export type Customer = {
  id: number;
  email: string;
  name: string;
  is_vat_registered: boolean;
  stopaj_rate: string;
  default_shipping_cost: string;
  created_at: string;
  updated_at: string;
};

export type PlatformConnection = {
  id: number;
  customer_id: number;
  platform: "trendyol";
  seller_id: string;
  is_active: boolean;
  sync_start_date: string;
  last_sync_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ProfitBreakdown = {
  gross_revenue: string;
  commission: string;
  sale_vat: string;
  service_fee: string;
  shipping_cost: string;
  total_cogs: string;
  stopaj: string;
  net_profit: string;
  is_realized: boolean;
};

export type OrderSummary = {
  id: number;
  external_id: string;
  order_date: string;
  profit: ProfitBreakdown;
};

export type OrderItemRead = {
  id: number;
  external_id: string;
  barcode: string;
  quantity: number;
  return_quantity: number;
  unit_sale_price: string;
  vat_rate: string;
  commission_rate: string;
  campaign_discount: string;
  cogs_snapshot: string;
};

export type ShipmentPackageRead = {
  id: number;
  external_id: string;
  status: string;
  raw_status: string;
  package_service_fee: string;
  shipping_cost: string;
  items: OrderItemRead[];
};

export type OrderDetail = OrderSummary & {
  packages: ShipmentPackageRead[];
};

export type ProductProfitabilityRow = {
  barcode: string;
  units_sold: number;
  units_returned: number;
  gross_revenue: string;
  commission: string;
  total_cogs: string;
  item_net_profit: string;
};

export type SimulationResponse = {
  base_net_profit: string;
  simulated_net_profit: string;
  delta: string;
  discount_pct: string;
  volume_uplift_pct: string;
};

export type Page<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type CogsImportResult = {
  updated: number;
  created: number;
  errors: string[];
};
