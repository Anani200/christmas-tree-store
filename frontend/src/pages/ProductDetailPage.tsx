import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getProduct, type Product } from '../api/client';
import TreeImage from '../components/TreeImage';
import styles from './ProductDetailPage.module.css';

export default function ProductDetailPage() {
  const { productId } = useParams<{ productId: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!productId) return;
    getProduct(productId)
      .then(setProduct)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [productId]);

  if (loading) return <div className={styles.center}>🎄 Loading…</div>;
  if (error || !product)
    return (
      <div className={styles.error}>
        {error ?? 'Product not found.'}
        <br />
        <Link to="/">← Back to catalog</Link>
      </div>
    );

  const unavailable = product.availabilityStatus === 'OUT_OF_STOCK';

  return (
    <main className={styles.page}>
      <Link to="/" className={styles.back}>← Back to catalog</Link>
      <div className={styles.detail}>
        <div className={styles.imagePanel}>
          <TreeImage
            productId={product.productId}
            imageUrl={product.imageUrl || undefined}
            alt={product.name}
          />
        </div>
        <div className={styles.info}>
          <h1 className={styles.name}>{product.name}</h1>
          <p className={styles.meta}>
            {product.type} &bull; {product.height}
          </p>
          <p className={styles.price}>${product.price.toFixed(2)}</p>
          <p className={styles.description}>{product.description}</p>
          <div className={styles.care}>
            <strong>Care Instructions</strong>
            {product.careInstructions}
          </div>
          {unavailable ? (
            <p className={styles.soldOut}>This tree is currently out of stock.</p>
          ) : (
            <Link
              to={`/order/${product.productId}`}
              className={styles.orderBtn}
            >
              Order This Tree →
            </Link>
          )}
        </div>
      </div>
    </main>
  );
}



