// src/pages/BuyerDashboard.jsx
import { useAuth } from '../context/AuthContext';

export default function BuyerDashboard() {
  const { user, logout } = useAuth();
  
  return (
    <div className="min-h-screen p-8 bg-slate-900 text-white">
      <div className="max-w-4xl mx-auto">
        <header className="flex justify-between items-center mb-8 pb-4 border-b border-slate-700">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-green-400 to-emerald-500 bg-clip-text text-transparent">
            Buyer Dashboard
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
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700 h-48 flex items-center justify-center">
            <p className="text-slate-400">Winning Bids: 0</p>
          </div>
          <div className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700 h-48 flex items-center justify-center">
            <p className="text-slate-400">Watched Items: 0</p>
          </div>
        </div>
      </div>
    </div>
  );
}
