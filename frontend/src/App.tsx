import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import CatalogPage from './pages/CatalogPage';
import ProductDetailPage from './pages/ProductDetailPage';
import AuthPage from './pages/AuthPage';
import OrderFormPage from './pages/OrderFormPage';
import OrderConfirmationPage from './pages/OrderConfirmationPage';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Navbar />
        <Routes>
          <Route path="/" element={<CatalogPage />} />
          <Route path="/products/:productId" element={<ProductDetailPage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route
            path="/order/:productId"
            element={
              <ProtectedRoute>
                <OrderFormPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/order/confirmation"
            element={
              <ProtectedRoute>
                <OrderConfirmationPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<CatalogPage />} />
        </Routes>
        <footer style={{
          textAlign: 'center',
          padding: '1.5rem 1rem',
          background: '#041208',
          color: 'rgba(255,255,255,0.35)',
          fontSize: '0.78rem',
          letterSpacing: '0.04em',
          borderTop: '1px solid rgba(255,255,255,0.06)'
        }}>
          🎄 Christmas Tree Store &nbsp;·&nbsp; Fresh Cut · Local Pickup · Seasonal
        </footer>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
