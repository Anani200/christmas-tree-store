export interface Product {
  productId: string;
  name: string;
  type: string;
  height: string;
  price: number;
  description: string;
  careInstructions: string;
  imageUrl: string;
  availabilityStatus: 'AVAILABLE' | 'LOW_STOCK' | 'OUT_OF_STOCK';
  quantityAvailable: number;
}

export interface OrderPayload {
  productId: string;
  quantity: number;
  customerName: string;
  customerEmail: string;
  customerPhone: string;
  preferredPickupDate: string;
  notes?: string;
}

export interface OrderResponse {
  message: string;
  orderId: string;
  status: string;
  notificationStatus: string;
}

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:3000';

const REQUEST_TIMEOUT_MS = 10_000;
const MAX_GET_RETRIES = 3;
const RETRYABLE_STATUSES = new Set([429, 500, 502, 503, 504]);

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function fetchWithTimeout(input: string, init: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  return fetch(input, { ...init, signal: controller.signal }).finally(() =>
    clearTimeout(timer)
  );
}

async function fetchWithRetry(input: string, init: RequestInit = {}): Promise<Response> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= MAX_GET_RETRIES; attempt++) {
    if (attempt > 0) {
      // Exponential backoff with jitter: ~100ms, ~200ms, ~400ms
      const delay = Math.min(100 * 2 ** (attempt - 1) + Math.random() * 100, 5_000);
      await sleep(delay);
    }
    try {
      const res = await fetchWithTimeout(input, init);
      if (!RETRYABLE_STATUSES.has(res.status)) return res;
      lastError = new Error(`HTTP ${res.status}`);
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetchWithRetry(`${API_BASE}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error((body as { message: string }).message || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function getProducts(): Promise<Product[]> {
  const data = await get<{ products: Product[] }>('/api/products');
  return data.products;
}

export async function getProduct(productId: string): Promise<Product> {
  return get<Product>(`/api/products/${encodeURIComponent(productId)}`);
}

export async function submitOrder(
  payload: OrderPayload,
  idToken: string
): Promise<OrderResponse> {
  const res = await fetchWithTimeout(`${API_BASE}/api/orders`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${idToken}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error((body as { message: string }).message || res.statusText);
  }
  return res.json() as Promise<OrderResponse>;
}
