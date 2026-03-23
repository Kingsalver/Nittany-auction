// src/pages/SellerDashboard.jsx
import { useAuth } from '../context/AuthContext';

export default function SellerDashboard() {
  const { user, logout } = useAuth();
  
  return (
    <div className="min-h-screen p-8 bg-slate-900 text-white">
      <div className="max-w-4xl mx-auto">
        <header className="flex justify-between items-center mb-8 pb-4 border-b border-slate-700">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Seller Dashboard
          </h1>
          <div className="flex items-center gap-4">
            <span className="text-slate-300">Welcome, {user?.email}</span>
            <button 
              onClick={logout} 
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors border border-slate-700"
            >
              Sign Out
            </button>
          </div>
        </header>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700 h-32 flex items-center justify-center">
            <p className="text-slate-400">Total Sales: $0.00</p>
          </div>
          <div className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700 h-32 flex items-center justify-center">
            <p className="text-slate-400">Active Auctions: 0</p>
          </div>
          <div className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700 h-32 flex items-center justify-center">
            <p className="text-slate-400">Pending Messages: 0</p>
          </div>
        </div>
      </div>
    </div>
  );
}
