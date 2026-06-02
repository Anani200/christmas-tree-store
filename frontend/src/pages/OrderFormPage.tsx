import { useEffect, useState, type FormEvent } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getProduct, submitOrder, type Product } from '../api/client';
import { useAuth } from '../context/AuthContext';
import styles from './OrderFormPage.module.css';

export default function OrderFormPage() {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const { getIdToken, user } = useAuth();

  const [product, setProduct] = useState<Product | null>(null);
  const [loadingProduct, setLoadingProduct] = useState(true);
  const [productError, setProductError] = useState<string | null>(null);

  const [customerName, setCustomerName] = useState('');
  const [customerEmail, setCustomerEmail] = useState(user?.email ?? '');
  const [customerPhone, setCustomerPhone] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [preferredPickupDate, setPreferredPickupDate] = useState('');
  const [notes, setNotes] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!productId) return;
    getProduct(productId)
      .then(setProduct)
      .catch((e: Error) => setProductError(e.message))
      .finally(() => setLoadingProduct(false));
  }, [productId]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!productId) return;
    setFormError(null);
    setSubmitting(true);
    try {
      const idToken = await getIdToken();
      const result = await submitOrder(
        {
          productId,
          quantity,
          customerName,
          customerEmail,
          customerPhone,
          preferredPickupDate,
          notes: notes || undefined,
        },
        idToken
      );
      navigate('/order/confirmation', {
        state: { orderId: result.orderId, productName: product?.name },
      });
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to submit order');
    } finally {
      setSubmitting(false);
    }
  }

  if (loadingProduct) return <div className={styles.center}>Loading…</div>;
  if (productError || !product)
    return <div className={styles.error}>{productError ?? 'Product not found'}</div>;

  // Minimum pickup date: tomorrow
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const minDate = tomorrow.toISOString().split('T')[0];

  return (
    <main className={styles.page}>
      <h1 className={styles.title}>Order: {product.name}</h1>
      <p className={styles.subtitle}>
        ${product.price.toFixed(2)} &bull; {product.height} &bull; {product.type}
      </p>

      {formError && <p className={styles.error}>{formError}</p>}

      <form onSubmit={(e) => void handleSubmit(e)} className={styles.form}>
        <div className={styles.row}>
          <label className={styles.label}>
            Your Name *
            <input
              type="text"
              required
              maxLength={200}
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className={styles.input}
            />
          </label>
          <label className={styles.label}>
            Email *
            <input
              type="email"
              required
              value={customerEmail}
              onChange={(e) => setCustomerEmail(e.target.value)}
              className={styles.input}
            />
          </label>
        </div>

        <div className={styles.row}>
          <label className={styles.label}>
            Phone *
            <input
              type="tel"
              required
              maxLength={50}
              value={customerPhone}
              onChange={(e) => setCustomerPhone(e.target.value)}
              className={styles.input}
              placeholder="e.g. 555-123-4567"
            />
          </label>
          <label className={styles.label}>
            Quantity *
            <input
              type="number"
              required
              min={1}
              max={10}
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value, 10))}
              className={styles.input}
            />
          </label>
        </div>

        <label className={styles.label}>
          Preferred Pickup Date *
          <input
            type="date"
            required
            min={minDate}
            value={preferredPickupDate}
            onChange={(e) => setPreferredPickupDate(e.target.value)}
            className={styles.input}
          />
        </label>

        <label className={styles.label}>
          Notes (optional)
          <textarea
            maxLength={2000}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className={styles.textarea}
            placeholder="Any special requests or delivery instructions…"
            rows={3}
          />
        </label>

        <div className={styles.actions}>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className={styles.cancelBtn}
          >
            Cancel
          </button>
          <button type="submit" disabled={submitting} className={styles.submitBtn}>
            {submitting ? 'Placing Order…' : 'Place Order'}
          </button>
        </div>
      </form>
    </main>
  );
}
