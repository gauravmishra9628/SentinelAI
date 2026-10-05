import Sidebar from '../components/Sidebar';
import Header from '../components/Header';

const MainLayout = ({ children, title = 'Road Safety Dashboard', alertCount = 3, systemStatus = true }) => (
  <div className="app">
    <Sidebar />
    <main className="main-content">
      <Header alertCount={alertCount} systemStatus={systemStatus} />
      <div className="page-shell">
        {title && <div className="page-heading"><h2>{title}</h2></div>}
        {children}
      </div>
    </main>
  </div>
);

export default MainLayout;
