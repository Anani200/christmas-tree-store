import { useRef } from 'react';
import { Link } from 'react-router-dom';
import type { Product } from '../api/client';
import TreeImage from './TreeImage';
import styles from './TreeCard.module.css';

interface Props {
  product: Product;
  index?: number;
}

const statusLabel: Record<Product['availabilityStatus'], string> = {
  AVAILABLE: 'In Stock',
  LOW_STOCK: 'Low Stock',
  OUT_OF_STOCK: 'Out of Stock',
};

export default function TreeCard({ product, index = 0 }: Props) {
  const cardRef = useRef<HTMLDivElement>(null);
  const unavailable = product.availabilityStatus === 'OUT_OF_STOCK';

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current;
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const rotX = ((y - cy) / cy) * -9;
    const rotY = ((x - cx) / cx) * 9;
    card.style.transform =
      `perspective(900px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateZ(8px) scale(1.02)`;
    // Move the sheen overlay
    const sheen = card.querySelector<HTMLElement>(`.${styles.sheen}`);
    if (sheen) {
      const px = (x / rect.width) * 100;
      const py = (y / rect.height) * 100;
      sheen.style.background =
        `radial-gradient(circle at ${px}% ${py}%, rgba(255,255,255,0.18) 0%, transparent 65%)`;
      sheen.style.opacity = '1';
    }
  };

  const handleMouseLeave = () => {
    const card = cardRef.current;
    if (!card) return;
    card.style.transform =
      'perspective(900px) rotateX(0deg) rotateY(0deg) translateZ(0) scale(1)';
    const sheen = card.querySelector<HTMLElement>(`.${styles.sheen}`);
    if (sheen) sheen.style.opacity = '0';
  };

  return (
    <div
      className={`${styles.outer} ${unavailable ? styles.unavailable : ''}`}
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div
        ref={cardRef}
        className={styles.card}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        <div className={styles.sheen} />

        <div className={styles.imageWrap}>
          <TreeImage
            productId={product.productId}
            imageUrl={product.imageUrl || undefined}
            alt={product.name}
            className={styles.treeImg}
          />
          {product.availabilityStatus === 'LOW_STOCK' && (
            <span className={styles.urgency}>Only {product.quantityAvailable} left!</span>
          )}
        </div>

        <div className={styles.body}>
          <h3 className={styles.name}>{product.name}</h3>
          <p className={styles.meta}>
            {product.type}&nbsp;&bull;&nbsp;{product.height}
          </p>
          <p className={styles.price}>${product.price.toFixed(2)}</p>

          {product.availabilityStatus !== 'AVAILABLE' && (
            <span className={`${styles.badge} ${styles[product.availabilityStatus.toLowerCase()]}`}>
              {statusLabel[product.availabilityStatus]}
            </span>
          )}

          <Link
            to={`/products/${product.productId}`}
            className={`${styles.btn} ${unavailable ? styles.btnDisabled : ''}`}
            aria-disabled={unavailable}
            tabIndex={unavailable ? -1 : 0}
          >
            View Details
          </Link>
        </div>
      </div>
    </div>
  );
}
