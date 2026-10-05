import { BrowserRouter, Route, Routes } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import CommandCenter from './pages/CommandCenter';
import LiveMonitoringPage from './pages/LiveMonitoringPage';
import RiskDetectionPage from './pages/RiskDetectionPage';
import AlertsPage from './pages/AlertsPage';
import RoadMap from './pages/RoadMap';
import CamerasPage from './pages/CamerasPage';
import AnalyticsPage from './pages/AnalyticsPage';
import PredictiveRiskPage from './pages/PredictiveRiskPage';
import AIEnginePage from './pages/AIEnginePage';
import AIAssistantPage from './pages/AIAssistantPage';
import AICopilotPage from './pages/AICopilotPage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';
import SecurityPage from './pages/SecurityPage';
import EmergencyResponsePage from './pages/EmergencyResponsePage';
import IncidentsPage from './pages/IncidentsPage';
import IncidentDetailsPage from './pages/IncidentDetailsPage';
import InvestigationPage from './pages/InvestigationPage';
import NotFound from './pages/NotFound';
import './App.css';

const App = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<MainLayout><Dashboard /></MainLayout>} />
      <Route path="/command-center" element={<MainLayout><CommandCenter /></MainLayout>} />
      <Route path="/live-monitoring" element={<MainLayout><LiveMonitoringPage /></MainLayout>} />
      <Route path="/risk-detection" element={<MainLayout><RiskDetectionPage /></MainLayout>} />
      <Route path="/alerts" element={<MainLayout><AlertsPage /></MainLayout>} />
      <Route path="/road-map" element={<MainLayout><RoadMap /></MainLayout>} />
      <Route path="/cameras" element={<MainLayout><CamerasPage /></MainLayout>} />
      <Route path="/analytics" element={<MainLayout><AnalyticsPage /></MainLayout>} />
      <Route path="/ai-prediction" element={<MainLayout><PredictiveRiskPage /></MainLayout>} />
      <Route path="/ai-engine" element={<MainLayout><AIEnginePage /></MainLayout>} />
      <Route path="/ai-assistant" element={<MainLayout><AIAssistantPage /></MainLayout>} />
      <Route path="/settings" element={<MainLayout><SettingsPage /></MainLayout>} />
      <Route path="/security" element={<MainLayout><SecurityPage /></MainLayout>} />
      <Route path="/emergency-response" element={<MainLayout><EmergencyResponsePage /></MainLayout>} />
      <Route path="/incidents" element={<MainLayout><IncidentsPage /></MainLayout>} />
      <Route path="/incidents/:incidentId" element={<MainLayout><IncidentDetailsPage /></MainLayout>} />
      <Route path="/investigation/:incidentId?" element={<MainLayout><InvestigationPage /></MainLayout>} />
      <Route path="/ai-copilot" element={<AICopilotPage />} />
      <Route path="/reports" element={<ReportsPage />} />
      <Route path="*" element={<MainLayout><NotFound /></MainLayout>} />
    </Routes>
  </BrowserRouter>
);

export default App;
