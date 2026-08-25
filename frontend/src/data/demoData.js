export const demoDashboardData = {
  statistics: [
    { title: 'Active Cameras', value: 18, icon: 'CAM', trend: 'up', label: '+2 since yesterday', status: 'ONLINE' },
    { title: 'Vehicles Monitored', value: 1284, icon: 'CAR', trend: 'up', label: '+12.4% this week', status: 'PROCESSING' },
    { title: 'High Risk Events', value: 3, icon: 'RISK', trend: 'down', label: '-18% from last hour', status: 'DEGRADED' },
    { title: 'Safety Score', value: '94', icon: 'SAFE', trend: 'up', label: 'Regional average', status: 'ONLINE' },
  ],
  monitoring: [
    { id: 'CAM-001', location: 'Main Highway - Sector 7', status: 'PROCESSING', trafficLevel: 'Moderate', detectedVehicles: 47, detectedPedestrians: 12, riskLevel: 'LOW', lastUpdate: 'Demo: just now' },
    { id: 'CAM-014', location: 'Airport Road Junction', status: 'ONLINE', trafficLevel: 'Heavy', detectedVehicles: 83, detectedPedestrians: 21, riskLevel: 'HIGH', lastUpdate: 'Demo: 45 sec ago' },
    { id: 'CAM-022', location: 'Downtown School Zone', status: 'ONLINE', trafficLevel: 'Light', detectedVehicles: 19, detectedPedestrians: 34, riskLevel: 'MEDIUM', lastUpdate: 'Demo: 1 min ago' },
  ],
  risks: [
    { id: 1, riskScore: 91, detectedIssue: 'Wrong-way vehicle', location: 'Airport Road Junction', camera: 'CAM-014', timestamp: 'Demo: 2 min ago', confidence: 97, severity: 'CRITICAL', status: 'Active' },
    { id: 2, riskScore: 78, detectedIssue: 'Overspeeding cluster', location: 'NH-24 Highway', camera: 'CAM-008', timestamp: 'Demo: 5 min ago', confidence: 93, severity: 'HIGH', status: 'Monitoring' },
    { id: 3, riskScore: 62, detectedIssue: 'Pedestrian near fast lane', location: 'Downtown School Zone', camera: 'CAM-022', timestamp: 'Demo: 9 min ago', confidence: 88, severity: 'MEDIUM', status: 'Active' },
    { id: 4, riskScore: 28, detectedIssue: 'Sudden braking event', location: 'Main Highway - Sector 7', camera: 'CAM-001', timestamp: 'Demo: 15 min ago', confidence: 81, severity: 'LOW', status: 'Resolved' },
  ],
  alerts: [
    { id: 1, type: 'Collision warning', location: 'Airport Road Junction', timestamp: 'Demo: 2 min ago', severity: 'CRITICAL', status: 'Active' },
    { id: 2, type: 'Overspeeding', location: 'NH-24 Highway', timestamp: 'Demo: 5 min ago', severity: 'HIGH', status: 'Monitoring' },
    { id: 3, type: 'Pedestrian risk', location: 'Downtown School Zone', timestamp: 'Demo: 9 min ago', severity: 'MEDIUM', status: 'Active' },
    { id: 4, type: 'Wrong-way driving', location: 'Sector 3 Ramp', timestamp: 'Demo: 13 min ago', severity: 'CRITICAL', status: 'Resolved' },
    { id: 5, type: 'Accident risk', location: 'Ring Road Exit 11', timestamp: 'Demo: 21 min ago', severity: 'MEDIUM', status: 'Monitoring' },
  ],
  analytics: {
    metrics: [
      { label: 'Risk Trend', value: '-18%', percent: 82, tone: 'safe' },
      { label: 'Incidents Today', value: '12', percent: 42, tone: 'warning' },
      { label: 'Traffic Density', value: '67%', percent: 67, tone: 'warning' },
      { label: 'Detection Accuracy', value: '96%', percent: 96, tone: 'safe' },
    ],
    trends: [
      { label: '06:00', incidents: 2, riskScore: 34 },
      { label: '09:00', incidents: 6, riskScore: 58 },
      { label: '12:00', incidents: 4, riskScore: 49 },
      { label: '15:00', incidents: 8, riskScore: 72 },
      { label: '18:00', incidents: 5, riskScore: 61 },
    ],
  },
  aiEngineStatus: {
    status: 'ONLINE',
    modelStatus: 'RoadRisk-v2 active',
    inferenceStatus: 'PROCESSING',
    cameraProcessingStatus: 'PROCESSING',
    apiStatus: 'OFFLINE',
    lastProcessedEvent: 'Demo: CAM-014 wrong-way vehicle, 2 min ago',
    uptime: '99.9%',
    modelVersion: 'v2.4.1',
  },
};
