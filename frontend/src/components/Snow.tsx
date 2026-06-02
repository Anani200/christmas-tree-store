import { useMemo } from 'react';
import styles from './Snow.module.css';

const FLAKE_COUNT = 30;

export default function Snow() {
  const flakes = useMemo(() => (
    Array.from({ length: FLAKE_COUNT }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      size: 0.4 + Math.random() * 0.7,
      duration: 6 + Math.random() * 10,
      delay: -Math.random() * 14,
      drift: (Math.random() - 0.5) * 60,
    }))
  ), []);

  return (
    <div className={styles.container} aria-hidden="true">
      {flakes.map((f) => (
        <div
          key={f.id}
          className={styles.flake}
          style={{
            left: `${f.left}%`,
            width: `${f.size}rem`,
            height: `${f.size}rem`,
            animationDuration: `${f.duration}s`,
            animationDelay: `${f.delay}s`,
            '--drift': `${f.drift}px`,
          } as React.CSSProperties}
        />
      ))}
    </div>
  );
}
