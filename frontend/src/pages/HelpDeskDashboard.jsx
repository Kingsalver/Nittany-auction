// src/pages/HelpDeskDashboard.jsx
import { useAuth } from '../context/AuthContext';

export default function HelpDeskDashboard() {
  const { user, logout } = useAuth();
  
  return (
    <div className="min-h-screen p-8 bg-slate-900 text-white">
      <div className="max-w-4xl mx-auto">
        <header className="flex justify-between items-center mb-8 pb-4 border-b border-slate-700">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-400 to-red-400 bg-clip-text text-transparent">
            Help Desk
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

        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
           <h2 className="text-xl font-semibold mb-4">Support Tickets</h2>
           <p className="text-slate-400">No active tickets.</p>
        </div>
      </div>
    </div>
  );
}
