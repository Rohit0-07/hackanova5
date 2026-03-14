import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, BellOff, Mail, X, CheckCircle, Loader, ChevronRight } from 'lucide-react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

/**
 * EmailNotifyToast
 *
 * Shows a toast when analysis starts asking if the user wants an email notification.
 * Workflow:
 *   1. Toast appears: "Get notified by email when done?" [Yes] [No thanks]
 *   2a. "Yes" → inline email input form → submit → success state
 *   2b. "No thanks" → toast closes, a small BellButton stays visible in the corner
 *
 * Props:
 *   sessionId        {string}  - current pipeline session ID
 *   isAnalysisRunning {boolean} - whether analysis is running (triggers toast)
 *   onSubscribed     {function} - called with email after successful registration
 */

// ─── Small "re-enable bell" button that stays after user dismisses ────────────
export const BellButton = ({ onClick }) => (
  <motion.button
    initial={{ opacity: 0, scale: 0.7 }}
    animate={{ opacity: 1, scale: 1 }}
    exit={{ opacity: 0, scale: 0.7 }}
    whileHover={{ scale: 1.08 }}
    whileTap={{ scale: 0.95 }}
    onClick={onClick}
    title="Get notified by email when done"
    className="fixed bottom-6 right-6 z-40 flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2.5 rounded-full shadow-[0_8px_24px_rgba(99,102,241,0.4)] transition-all border border-indigo-400/30"
  >
    <Bell size={14} className="shrink-0" />
    Notify me
  </motion.button>
);

// ─── Main Toast component ─────────────────────────────────────────────────────
const EmailNotifyToast = ({ sessionId, isAnalysisRunning, onSubscribed }) => {
  const [phase, setPhase] = useState('hidden');
  // phases: hidden | ask | form | loading | success | dismissed

  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [showBell, setShowBell] = useState(false);

  // Show the ask toast as soon as a session starts
  useEffect(() => {
    if (isAnalysisRunning && sessionId) {
      setPhase('ask');
      setShowBell(false);
    }
  }, [isAnalysisRunning, sessionId]);

  const handleYes = () => setPhase('form');

  const handleNo = () => {
    setPhase('dismissed');
    setShowBell(true);
  };

  const handleBellClick = () => {
    setShowBell(false);
    setPhase('form');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !email.includes('@')) {
      setError('Please enter a valid email address.');
      return;
    }
    setError('');
    setPhase('loading');

    try {
      const res = await fetch(`${API_BASE}/notify/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, email }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        setPhase('success');
        if (onSubscribed) onSubscribed(email);
        // Auto-dismiss after 4 seconds
        setTimeout(() => setPhase('hidden'), 4000);
      } else {
        setError(data.detail || 'Failed to register. Try again.');
        setPhase('form');
      }
    } catch (err) {
      setError('Network error. Please try again.');
      setPhase('form');
    }
  };

  const isVisible = phase !== 'hidden' && phase !== 'dismissed';

  return (
    <>
      {/* Main Toast */}
      <AnimatePresence>
        {isVisible && (
          <motion.div
            key="email-toast"
            initial={{ opacity: 0, y: 30, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: 'spring', damping: 22, stiffness: 300, mass: 0.6 }}
            className="fixed bottom-6 right-6 z-50 w-80 bg-slate-900 border border-slate-700/60 rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.6)] overflow-hidden"
          >
            {/* Top accent */}
            <div className="h-0.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />

            {/* ASK phase */}
            {phase === 'ask' && (
              <div className="p-5">
                <div className="flex items-start gap-3">
                  <div className="shrink-0 w-9 h-9 rounded-xl bg-indigo-500/15 border border-indigo-500/25 flex items-center justify-center">
                    <Bell size={16} className="text-indigo-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-white leading-snug">
                      Get notified when done?
                    </p>
                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                      We'll email you a link back to this session when analysis completes.
                    </p>
                  </div>
                  <button onClick={handleNo} className="shrink-0 text-slate-600 hover:text-slate-400 transition-colors mt-0.5">
                    <X size={15} />
                  </button>
                </div>
                <div className="flex items-center gap-2 mt-4">
                  <button
                    onClick={handleYes}
                    className="flex-1 flex items-center justify-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold py-2.5 rounded-xl transition-all shadow-lg hover:shadow-indigo-500/25"
                  >
                    <Mail size={12} />
                    Yes, notify me
                    <ChevronRight size={11} />
                  </button>
                  <button
                    onClick={handleNo}
                    className="flex-1 text-xs text-slate-400 hover:text-slate-200 font-semibold py-2.5 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700/40 transition-all"
                  >
                    No thanks
                  </button>
                </div>
              </div>
            )}

            {/* FORM phase */}
            {phase === 'form' && (
              <form onSubmit={handleSubmit} className="p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Mail size={14} className="text-indigo-400 shrink-0" />
                  <p className="text-sm font-bold text-white">Enter your email</p>
                  <button
                    type="button"
                    onClick={handleNo}
                    className="ml-auto text-slate-600 hover:text-slate-400 transition-colors"
                  >
                    <X size={14} />
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 mb-3 leading-relaxed">
                  You'll receive a direct link back to this session when analysis is complete.
                </p>
                <input
                  type="email"
                  value={email}
                  onChange={e => { setEmail(e.target.value); setError(''); }}
                  placeholder="you@example.com"
                  autoFocus
                  className="w-full bg-slate-800/70 border border-slate-700/60 focus:border-indigo-500/60 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition-colors mb-2"
                />
                {error && (
                  <p className="text-[11px] text-rose-400 mb-2">{error}</p>
                )}
                <button
                  type="submit"
                  className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold py-2.5 rounded-xl transition-all mt-1"
                >
                  <Bell size={12} />
                  Notify me when done
                </button>
              </form>
            )}

            {/* LOADING phase */}
            {phase === 'loading' && (
              <div className="p-5 flex items-center gap-3">
                <Loader size={18} className="text-indigo-400 animate-spin shrink-0" />
                <p className="text-sm text-slate-300 font-medium">Registering notification…</p>
              </div>
            )}

            {/* SUCCESS phase */}
            {phase === 'success' && (
              <div className="p-5 flex items-start gap-3">
                <CheckCircle size={18} className="text-emerald-400 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-bold text-emerald-300">All set!</p>
                  <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                    We'll send a link to <span className="text-white font-semibold">{email}</span> when the analysis finishes.
                  </p>
                </div>
                <button onClick={() => setPhase('hidden')} className="ml-auto text-slate-600 hover:text-slate-400 transition-colors shrink-0">
                  <X size={14} />
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating bell button after user dismisses */}
      <AnimatePresence>
        {showBell && isAnalysisRunning && (
          <BellButton key="bell-btn" onClick={handleBellClick} />
        )}
      </AnimatePresence>
    </>
  );
};

export default EmailNotifyToast;
