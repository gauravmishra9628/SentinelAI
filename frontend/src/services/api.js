import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 5000,
});

api.interceptors.request.use(
  config => config,
  error => Promise.reject(error)
);

api.interceptors.response.use(
  response => response,
  error => {
    if (!error.response) {
      return Promise.reject(new Error('Backend unavailable'));
    }
    return Promise.reject(error);
  }
);

export const getHealth = () => api.get('/api/health').then(response => response.data);
export const getDashboard = () => api.get('/api/dashboard').then(response => response.data);
export const getLiveMonitoring = () => api.get('/api/live-monitoring').then(response => response.data);
export const getRiskDetection = () => api.get('/api/risk-detection').then(response => response.data);
export const getAlerts = () => api.get('/api/alerts').then(response => response.data);
export const getAnalytics = () => api.get('/api/analytics').then(response => response.data);
export const getAIEngineStatus = () => api.get('/api/ai-engine/status').then(response => response.data);

export default api;
