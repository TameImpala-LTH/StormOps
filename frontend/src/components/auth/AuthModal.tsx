import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Mail, Lock, User as UserIcon, AlertCircle } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: 'login' | 'register';
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, initialMode = 'login' }) => {
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  React.useEffect(() => {
    if (isOpen) {
      setMode(initialMode);
      setError(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const { login, register } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        if (!displayName.trim()) {
          setError('Display name is required.');
          setIsSubmitting(false);
          return;
        }
        await register(email, password, displayName);
      }
      onClose();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axErr = err as {
          response?: {
            status?: number;
            data?: { detail?: string | Array<{ msg?: string }> };
          };
        };
        const status = axErr.response?.status;
        const detail = axErr.response?.data?.detail;

        if (status === 401) {
          setError(typeof detail === 'string' ? detail : 'Invalid email or password.');
        } else if (
          status === 409 ||
          (status === 400 && typeof detail === 'string' && detail.toLowerCase().includes('already exists'))
        ) {
          setError(typeof detail === 'string' ? detail : 'An account with this email address already exists.');
        } else if (status === 422) {
          if (Array.isArray(detail) && detail.length > 0 && detail[0].msg) {
            setError(detail[0].msg);
          } else if (typeof detail === 'string') {
            setError(detail);
          } else {
            setError('Please verify email and password meet requirements.');
          }
        } else if (
          status === 503 ||
          (typeof detail === 'string' && detail.toLowerCase().includes('database'))
        ) {
          setError('Database service is currently unavailable. Please check database connection.');
        } else if (status === 500) {
          setError('An unexpected server error occurred. Please try again shortly.');
        } else if (typeof detail === 'string' && detail.trim()) {
          setError(detail);
        } else {
          setError(
            mode === 'login'
              ? 'Authentication failed. Please check credentials.'
              : 'Registration failed. Please check details and try again.'
          );
        }
      } else {
        setError('Network error. Unable to connect to StormOps server.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="auth-modal-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        >
          <motion.div
            key="auth-modal-dialog"
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label={mode === 'login' ? 'Sign in to StormOps' : 'Create an Account'}
            className="w-full max-w-md rounded-3xl p-6 sm:p-8 shadow-2xl relative border"
            style={{
              backgroundColor: 'var(--surface)',
              borderColor: 'var(--border)',
              color: 'var(--text-primary)',
            }}
          >
            {/* Close button */}
            <button
              type="button"
              onClick={onClose}
              className="absolute top-5 right-5 p-2 rounded-full hover:opacity-75 transition-opacity cursor-pointer"
              style={{ color: 'var(--text-muted)' }}
            >
              <X className="w-5 h-5" />
            </button>

          {/* Title */}
          <div className="mb-6">
            <h3 className="text-xl font-medium tracking-tight">
              {mode === 'login' ? 'Sign in to StormOps' : 'Create an Account'}
            </h3>
            <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
              {mode === 'login'
                ? 'Access your personal WeatherGPT search history and saved locations.'
                : 'Save your favorite cities and keep your conversation history synchronized.'}
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-4 p-3 rounded-xl flex items-center gap-2 text-xs bg-rose-500/10 border border-rose-500/25 text-rose-400">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label className="block text-xs font-mono mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  DISPLAY NAME
                </label>
                <div
                  className="flex items-center gap-2 px-3 py-2.5 rounded-xl border"
                  style={{ backgroundColor: 'var(--surface-elevated)', borderColor: 'var(--border-muted)' }}
                >
                  <UserIcon className="w-4 h-4 text-zinc-400" />
                  <input
                    type="text"
                    name="name"
                    autoComplete="name"
                    required
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="e.g. Alex Morgan"
                    className="w-full bg-transparent text-sm outline-none"
                    style={{ color: 'var(--text-primary)' }}
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-mono mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                EMAIL ADDRESS
              </label>
              <div
                className="flex items-center gap-2 px-3 py-2.5 rounded-xl border"
                style={{ backgroundColor: 'var(--surface-elevated)', borderColor: 'var(--border-muted)' }}
              >
                <Mail className="w-4 h-4 text-zinc-400" />
                <input
                  type="email"
                  name="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="w-full bg-transparent text-sm outline-none"
                  style={{ color: 'var(--text-primary)' }}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                PASSWORD
              </label>
              <div
                className="flex items-center gap-2 px-3 py-2.5 rounded-xl border"
                style={{ backgroundColor: 'var(--surface-elevated)', borderColor: 'var(--border-muted)' }}
              >
                <Lock className="w-4 h-4 text-zinc-400" />
                <input
                  type="password"
                  name="password"
                  autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-transparent text-sm outline-none"
                  style={{ color: 'var(--text-primary)' }}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 py-3 rounded-xl text-sm font-medium transition-all cursor-pointer disabled:opacity-50"
              style={{
                backgroundColor: 'var(--accent)',
                color: 'var(--btn-primary-text)',
              }}
            >
              {isSubmitting
                ? 'Please wait...'
                : mode === 'login'
                ? 'Sign In'
                : 'Create Account'}
            </button>
          </form>

          {/* Mode Switcher */}
          <div className="mt-6 pt-4 text-center border-t text-xs" style={{ borderColor: 'var(--border-muted)' }}>
            {mode === 'login' ? (
              <p style={{ color: 'var(--text-secondary)' }}>
                Don't have an account?{' '}
                <button
                  type="button"
                  data-testid="switch-to-register"
                  onClick={() => {
                    setMode('register');
                    setError(null);
                  }}
                  className="font-semibold underline cursor-pointer hover:opacity-80"
                  style={{ color: 'var(--accent)' }}
                >
                  Sign Up
                </button>
              </p>
            ) : (
              <p style={{ color: 'var(--text-secondary)' }}>
                Already have an account?{' '}
                <button
                  type="button"
                  data-testid="switch-to-login"
                  onClick={() => {
                    setMode('login');
                    setError(null);
                  }}
                  className="font-semibold underline cursor-pointer hover:opacity-80"
                  style={{ color: 'var(--accent)' }}
                >
                  Sign In
                </button>
              </p>
            )}
          </div>
        </motion.div>
      </motion.div>
    )}
  </AnimatePresence>
);
};
