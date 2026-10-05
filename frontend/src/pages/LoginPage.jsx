const LoginPage = () => (
  <div className="page-content auth-page">
    <div className="panel-card auth-card">
      <h2>SentinelAI Login</h2>
      <label>
        <span>Username</span>
        <input type="text" defaultValue="operator" />
      </label>
      <label>
        <span>Password</span>
        <input type="password" defaultValue="********" />
      </label>
      <button className="primary-btn" type="button">Sign in</button>
    </div>
  </div>
);

export default LoginPage;
