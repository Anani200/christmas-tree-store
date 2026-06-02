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
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
