import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import SellerDashboard from './pages/SellerDashboard';
import BuyerDashboard from './pages/BuyerDashboard';
import HelpDeskDashboard from './pages/HelpDeskDashboard';
import AuthGuard from './components/AuthGuard';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Navigate to="/login" replace />} />
        
        <Route path="/seller" element={<AuthGuard role="Seller"><SellerDashboard /></AuthGuard>} />
        <Route path="/buyer" element={<AuthGuard role="Buyer"><BuyerDashboard /></AuthGuard>} />
        <Route path="/helpdesk" element={<AuthGuard role="HelpDesk"><HelpDeskDashboard /></AuthGuard>} />
      </Routes>
    </Router>
  );
}

export default App;
