import { useEffect, useState } from 'react';
import { getProducts, type Product } from '../api/client';
import TreeCard from '../components/TreeCard';
import Snow from '../components/Snow';
import styles from './CatalogPage.module.css';

export default function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProducts()
      .then(setProducts)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className={styles.center}>🎄 Loading trees…</div>;
  if (error) return <div className={styles.error}>Error: {error}</div>;

  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <Snow />
        <div className={styles.heroContent}>
          <p className={styles.heroEyebrow}>❆ Fresh Cut • Local Pickup • Seasonal</p>
          <h1 className={styles.heroTitle}>Find Your Perfect<br />Christmas Tree</h1>
          <p className={styles.heroSub}>
            Hand-selected fresh-cut trees. Order before they sell out!
          </p>
          <div className={styles.heroBadges}>
            <span className={styles.heroBadge}>🌲 Fresh Cut</span>
            <span className={styles.heroBadge}>📍 Local Pickup</span>
            <span className={styles.heroBadge}>❄️ Seasonal Selection</span>
          </div>
        </div>
      </header>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Product Catalog</h2>
          <p className={styles.sectionSub}>{products.length} varieties available this season</p>
        </div>
        <div className={styles.grid}>
          {products.map((p, i) => (
            <TreeCard key={p.productId} product={p} index={i} />
          ))}
        </div>
      </section>
    </main>
  );
}
