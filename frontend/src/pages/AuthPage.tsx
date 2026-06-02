import { useState, type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styles from './AuthPage.module.css';

type Mode = 'signin' | 'signup' | 'confirm';

export default function AuthPage() {
  const { login, register, confirmRegistration } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirect = searchParams.get('redirect') ?? '/';

  const [mode, setMode] = useState<Mode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === 'signin') {
        await login(email, password);
        navigate(redirect, { replace: true });
      } else if (mode === 'signup') {
        await register(email, password);
        setMode('confirm');
      } else {
        await confirmRegistration(email, code);
        await login(email, password);
        navigate(redirect, { replace: true });
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>
          {mode === 'signin'
            ? 'Sign In'
            : mode === 'signup'
            ? 'Create Account'
            : 'Verify Email'}
        </h1>

        {error && <p className={styles.error}>{error}</p>}

        <form onSubmit={(e) => void handleSubmit(e)} className={styles.form}>
          {mode !== 'confirm' && (
            <>
              <label className={styles.label}>
                Email
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={styles.input}
                  autoComplete="email"
                />
              </label>
              <label className={styles.label}>
                Password
                <input
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={styles.input}
                  autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                />
              </label>
            </>
          )}

          {mode === 'confirm' && (
            <label className={styles.label}>
              Verification Code
              <input
                type="text"
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className={styles.input}
                placeholder="Check your email"
                autoComplete="one-time-code"
              />
            </label>
          )}

          <button type="submit" disabled={submitting} className={styles.btn}>
            {submitting
              ? 'Please wait…'
              : mode === 'signin'
              ? 'Sign In'
              : mode === 'signup'
              ? 'Create Account'
              : 'Verify'}
          </button>
        </form>

        <div className={styles.toggle}>
          {mode === 'signin' ? (
            <p>
              No account?{' '}
              <button className={styles.link} onClick={() => setMode('signup')}>
                Sign up
              </button>
            </p>
          ) : mode === 'signup' ? (
            <p>
              Already have an account?{' '}
              <button className={styles.link} onClick={() => setMode('signin')}>
                Sign in
              </button>
            </p>
          ) : null}
        </div>
      </div>
    </main>
  );
}
