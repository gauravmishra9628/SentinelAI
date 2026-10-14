import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../services/api';
import './LoginPage.css';

const LoginPage = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(username, password);
      navigate('/emergency-response', { replace: true });
      window.location.reload();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Login failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login-page">
      <form className="login-panel" onSubmit={submit}>
        <div className="login-brand">SentinelAI</div>
        <h1>Operator sign in</h1>
        <p>Authenticate to access the safety operations platform.</p>
        {error && <div className="login-error" role="alert">{error}</div>}
        <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></label>
        <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
        <button type="submit" disabled={busy}>{busy ? 'Signing in...' : 'Sign in'}</button>
      </form>
    </main>
  );
};

export default LoginPage;
