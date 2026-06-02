import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getProducts, getProduct, submitOrder } from '../api/client';

// Replace global fetch with a vi mock
const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch);
  // Reset VITE_API_URL via import.meta.env is not easily mutable;
  // the default fallback 'http://localhost:3000' is used in tests.
});

afterEach(() => {
  vi.restoreAllMocks();
});

function mockResponse(body: unknown, status = 200) {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    statusText: status === 200 ? 'OK' : 'Error',
  });
}

describe('API client', () => {
  describe('getProducts', () => {
    it('returns the products array', async () => {
      const products = [{ productId: 'tree-001', name: 'Fraser Fir', price: 89.99 }];
      mockResponse({ products });
      const result = await getProducts();
      expect(result).toEqual(products);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/products')
      );
    });

    it('throws on non-ok response', async () => {
      mockResponse({ message: 'Server error' }, 500);
      await expect(getProducts()).rejects.toThrow('Server error');
    });
  });

  describe('getProduct', () => {
    it('fetches a single product by id', async () => {
      const product = { productId: 'tree-001', name: 'Fraser Fir' };
      mockResponse(product);
      const result = await getProduct('tree-001');
      expect(result).toEqual(product);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/products/tree-001')
      );
    });
  });

  describe('submitOrder', () => {
    const payload = {
      productId: 'tree-001',
      quantity: 1,
      customerName: 'Jane Doe',
      customerEmail: 'jane@example.com',
      customerPhone: '555-1234',
      preferredPickupDate: '2024-12-20',
    };

    it('sends Authorization Bearer header', async () => {
      mockResponse({ orderId: 'ord-abc', message: 'ok', status: 'PENDING', notificationStatus: 'QUEUED' });
      await submitOrder(payload, 'test-id-token');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/orders'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            Authorization: 'Bearer test-id-token',
          }),
        })
      );
    });

    it('returns the order response on success', async () => {
      const orderResp = { orderId: 'ord-abc', message: 'ok', status: 'PENDING', notificationStatus: 'QUEUED' };
      mockResponse(orderResp);
      const result = await submitOrder(payload, 'token');
      expect(result.orderId).toBe('ord-abc');
    });

    it('throws on 401 response', async () => {
      mockResponse({ message: 'Unauthorized' }, 401);
      await expect(submitOrder(payload, 'bad-token')).rejects.toThrow('Unauthorized');
    });
  });
});
