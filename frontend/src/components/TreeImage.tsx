import styles from './TreeImage.module.css';

interface TreeConfig {
  bg: [string, string];
  layers: [string, string, string];
  trunk: string;
  ornaments: string[];
  starColor: string;
}

const CONFIGS: Record<string, TreeConfig> = {
  'tree-001': {
    bg: ['#061a0f', '#102a1c'],
    layers: ['#1a5c20', '#22762a', '#2d8c34'],
    trunk: '#6b3a20',
    ornaments: ['#e74c3c', '#f0c040', '#c0392b', '#f39c12', '#e74c3c'],
    starColor: '#f0c040',
  },
  'tree-002': {
    bg: ['#060d1a', '#0d1e2e'],
    layers: ['#145c28', '#1a7030', '#22883a'],
    trunk: '#5a3420',
    ornaments: ['#e74c3c', '#3498db', '#f0c040', '#9b59b6', '#2ecc71'],
    starColor: '#f0c040',
  },
  'tree-003': {
    bg: ['#071a08', '#0e2e10'],
    layers: ['#1e6620', '#288428', '#33963a'],
    trunk: '#7a4030',
    ornaments: ['#95a5a6', '#bdc3c7', '#ecf0f1', '#7f8c8d', '#3498db'],
    starColor: '#ecf0f1',
  },
  'tree-004': {
    bg: ['#060a1a', '#0a102e'],
    layers: ['#2a5a7a', '#3472a0', '#4088b8'],
    trunk: '#5c4a38',
    ornaments: ['#ecf0f1', '#74b9ff', '#dfe6e9', '#a0c4e8', '#74b9ff'],
    starColor: '#74b9ff',
  },
  'tree-005': {
    bg: ['#0f1a06', '#1a2e0a'],
    layers: ['#1c5218', '#245e22', '#2e6e2a'],
    trunk: '#6a3a1c',
    ornaments: ['#e67e22', '#f39c12', '#e74c3c', '#f0c040', '#e67e22'],
    starColor: '#f39c12',
  },
};

const DEFAULT_CONFIG = CONFIGS['tree-001'];

const LIGHT_COLORS = ['#e74c3c', '#f0c040', '#3498db', '#2ecc71', '#9b59b6'];

const LIGHTS = [
  { cx: 94,  cy: 250, di: 0 },
  { cx: 138, cy: 218, di: 1 },
  { cx: 200, cy: 262, di: 2 },
  { cx: 162, cy: 182, di: 3 },
  { cx: 120, cy: 210, di: 4 },
  { cx: 178, cy: 234, di: 0 },
  { cx: 108, cy: 184, di: 1 },
  { cx: 156, cy: 252, di: 2 },
  { cx: 216, cy: 246, di: 3 },
  { cx: 72,  cy: 272, di: 4 },
  { cx: 228, cy: 274, di: 0 },
  { cx: 144, cy: 168, di: 1 },
];

const ORNAMENT_POSITIONS = [
  { cx: 108, cy: 234 },
  { cx: 192, cy: 246 },
  { cx: 148, cy: 198 },
  { cx: 170, cy: 270 },
  { cx: 126, cy: 270 },
];

interface Props {
  productId: string;
  imageUrl?: string;
  alt: string;
  className?: string;
}

export default function TreeImage({ productId, imageUrl, alt, className }: Props) {
  const config = CONFIGS[productId] ?? DEFAULT_CONFIG;

  if (imageUrl) {
    return (
      <div className={`${styles.wrapper} ${className ?? ''}`}>
        <img
          src={imageUrl}
          alt={alt}
          className={styles.realImage}
          onError={(e) => {
            e.currentTarget.style.display = 'none';
            const fb = e.currentTarget.nextElementSibling as HTMLElement | null;
            if (fb) fb.style.display = 'flex';
          }}
        />
        <div className={styles.svgFallback} style={{ display: 'none' }}>
          <TreeSVG config={config} productId={productId} />
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.wrapper} ${className ?? ''}`}>
      <TreeSVG config={config} productId={productId} />
    </div>
  );
}

function TreeSVG({ config, productId }: { config: TreeConfig; productId: string }) {
  const bgId = `bg-${productId}`;
  const glowId = `glow-${productId}`;
  const softId = `soft-${productId}`;

  return (
    <svg
      viewBox="0 0 300 360"
      xmlns="http://www.w3.org/2000/svg"
      className={styles.svg}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={bgId} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor={config.bg[0]} />
          <stop offset="100%" stopColor={config.bg[1]} />
        </linearGradient>
        <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id={softId} x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="5" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      {/* Background */}
      <rect width="300" height="360" fill={`url(#${bgId})`} />

      {/* Background stars */}
      {([28,82,250,268,15,290,160,50,240] as number[]).map((x, i) => {
        const ys = [38, 18, 62, 28, 80, 78, 22, 105, 100];
        return (
          <circle
            key={i} cx={x} cy={ys[i]}
            r={i % 2 === 0 ? 1.5 : 1}
            fill="white"
            opacity={0.25 + (i % 3) * 0.12}
          />
        );
      })}

      {/* Ground snow */}
      <ellipse cx="150" cy="340" rx="110" ry="16" fill="rgba(255,255,255,0.15)" />
      <ellipse cx="150" cy="336" rx="80" ry="10" fill="rgba(255,255,255,0.22)" />

      {/* Trunk */}
      <rect x="132" y="288" width="36" height="46" fill={config.trunk} rx="3" />
      <rect x="136" y="291" width="10" height="40" fill="rgba(255,255,255,0.08)" rx="1" />

      {/* Bottom tier */}
      <polygon points="14,292 150,152 286,292" fill={config.layers[0]} />
      <polygon points="20,286 150,160 280,286" fill={config.layers[1]} />
      <polygon points="14,292 48,292 150,228 252,292 286,292 150,268"
        fill="rgba(255,255,255,0.07)" />

      {/* Middle tier */}
      <polygon points="48,226 150,100 252,226" fill={config.layers[0]} />
      <polygon points="54,220 150,107 246,220" fill={config.layers[1]} />
      <polygon points="48,226 76,226 150,190 224,226 252,226 150,208"
        fill="rgba(255,255,255,0.07)" />

      {/* Upper tier */}
      <polygon points="80,162 150,50 220,162" fill={config.layers[0]} />
      <polygon points="86,156 150,57 214,156" fill={config.layers[1]} />
      <polygon points="80,162 104,162 150,132 196,162 220,162 150,146"
        fill="rgba(255,255,255,0.07)" />

      {/* Top tier */}
      <polygon points="110,102 150,24 190,102" fill={config.layers[1]} />
      <polygon points="114,96 150,30 186,96" fill={config.layers[2]} />

      {/* Lights */}
      {LIGHTS.map((l, i) => (
        <circle
          key={i}
          cx={l.cx} cy={l.cy} r="4.5"
          fill={LIGHT_COLORS[l.di % LIGHT_COLORS.length]}
          filter={`url(#${glowId})`}
          className={styles.light}
          style={{ animationDelay: `${(l.di * 0.3 + i * 0.1).toFixed(1)}s` }}
        />
      ))}

      {/* Ornaments */}
      {ORNAMENT_POSITIONS.map((pos, i) => (
        <g key={i}>
          <circle cx={pos.cx} cy={pos.cy} r="9.5" fill={config.ornaments[i]} />
          <circle cx={pos.cx - 3} cy={pos.cy - 3} r="3.5" fill="rgba(255,255,255,0.4)" />
          <line
            x1={pos.cx} y1={pos.cy - 9} x2={pos.cx} y2={pos.cy - 15}
            stroke="rgba(255,255,255,0.45)" strokeWidth="1.5"
          />
        </g>
      ))}

      {/* Top star */}
      <text
        x="150" y="30"
        textAnchor="middle"
        fontSize="22"
        fill={config.starColor}
        filter={`url(#${softId})`}
        className={styles.star}
        style={{ transformOrigin: '150px 22px' }}
      >★</text>
    </svg>
  );
}
