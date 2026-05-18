// Backend API client. Tüm endpoint çağrıları burada toplanır.
// .env.local üzerinden NEXT_PUBLIC_API_URL ile override edilebilir.

import type {
  CogsImportResult,
  Customer,
  OrderDetail,
  OrderSummary,
  Page,
  PlatformConnection,
  PriceSimulatorRequest,
  PriceSimulatorResponse,
  ProductProfitabilityRow,
  SimulationResponse,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(`API ${status}: ${detail}`);
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { json?: unknown }
): Promise<T> {
  const headers = new Headers(init?.headers);
  let body = init?.body;
  if (init?.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    body,
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // Customers
  listCustomers: () => request<Page<Customer>>(`/customers?limit=200`),
  getCustomer: (id: number) => request<Customer>(`/customers/${id}`),
  createCustomer: (data: {
    email: string;
    name: string;
    is_vat_registered?: boolean;
    stopaj_rate?: string;
    default_shipping_cost?: string;
  }) => request<Customer>(`/customers`, { method: "POST", json: data }),
  updateCustomer: (id: number, patch: Partial<Customer>) =>
    request<Customer>(`/customers/${id}`, { method: "PATCH", json: patch }),

  // Connections
  listConnections: (customerId: number) =>
    request<PlatformConnection[]>(`/customers/${customerId}/connections`),
  createConnection: (
    customerId: number,
    data: {
      platform: "trendyol";
      seller_id: string;
      api_key: string;
      api_secret: string;
    }
  ) =>
    request<PlatformConnection>(`/customers/${customerId}/connections`, {
      method: "POST",
      json: data,
    }),
  deleteConnection: (customerId: number, connectionId: number) =>
    request<void>(`/customers/${customerId}/connections/${connectionId}`, {
      method: "DELETE",
    }),
  updateConnection: (
    customerId: number,
    connectionId: number,
    patch: { is_active?: boolean; api_key?: string; api_secret?: string }
  ) =>
    request<PlatformConnection>(
      `/customers/${customerId}/connections/${connectionId}`,
      { method: "PATCH", json: patch }
    ),

  // COGS
  uploadCogs: async (customerId: number, file: File): Promise<CogsImportResult> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/customers/${customerId}/cogs`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, data.detail);
    }
    return res.json();
  },
  cogsTemplateUrl: (customerId: number) =>
    `${API_BASE}/customers/${customerId}/cogs/template`,

  // Reports
  listOrders: (customerId: number, limit = 50, offset = 0) =>
    request<Page<OrderSummary>>(
      `/customers/${customerId}/orders?limit=${limit}&offset=${offset}`
    ),
  getOrder: (customerId: number, orderId: number) =>
    request<OrderDetail>(`/customers/${customerId}/orders/${orderId}`),
  productProfitability: (customerId: number) =>
    request<ProductProfitabilityRow[]>(
      `/customers/${customerId}/products/profitability`
    ),
  simulate: (
    customerId: number,
    data: { discount_pct: string; volume_uplift_pct?: string }
  ) =>
    request<SimulationResponse>(`/customers/${customerId}/simulations`, {
      method: "POST",
      json: data,
    }),

  // Price Simulator
  simulatePrice: (customerId: number, data: PriceSimulatorRequest) =>
    request<PriceSimulatorResponse>(
      `/customers/${customerId}/price-simulator`,
      { method: "POST", json: data }
    ),
};

export { ApiError };
