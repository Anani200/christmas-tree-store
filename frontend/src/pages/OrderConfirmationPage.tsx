import { useLocation, Link } from 'react-router-dom';
import styles from './OrderConfirmationPage.module.css';

interface LocationState {
  orderId?: string;
  productName?: string;
}

export default function OrderConfirmationPage() {
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;
  const { orderId, productName } = state;

  return (
    <main className={styles.page}>
      <div className={styles.card}>
        <div className={styles.icon} aria-hidden="true">🎄</div>
        <h1 className={styles.title}>Order Confirmed!</h1>
        {productName && (
          <p className={styles.product}>
            Your <strong>{productName}</strong> is reserved.
          </p>
        )}
        {orderId && (
          <p className={styles.orderId}>
            Order ID: <code>{orderId}</code>
          </p>
        )}
        <p className={styles.message}>
          We will send a confirmation email shortly. Please bring your Order ID when
          picking up your tree.
        </p>
        <Link to="/" className={styles.btn}>
          Back to Shop
        </Link>
      </div>
    </main>
  );
}
