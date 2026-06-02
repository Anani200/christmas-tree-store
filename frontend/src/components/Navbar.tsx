import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styles from './Navbar.module.css';

export default function Navbar() {
  const { isAuthenticated, logout, user } = useAuth();

  return (
    <nav className={styles.navbar}>
      <Link to="/" className={styles.brand}>
        🎄 Christmas Tree Store
      </Link>
      <div className={styles.links}>
        <Link to="/">Shop</Link>
        {isAuthenticated ? (
          <>
            <span className={styles.userInfo}>{user?.email}</span>
            <button className={styles.logoutBtn} onClick={() => void logout()}>
              Sign Out
            </button>
          </>
        ) : (
          <Link to="/auth">Sign In</Link>
        )}
      </div>
    </nav>
  );
}
