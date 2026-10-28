import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000,
});

export const endpoints = {
  // Health
  getHealth: () => api.get('/health'),
  
  // Dashboard
  getDashboardSummary: () => api.get('/dashboard/summary'),
  getDashboardActivity: () => api.get('/dashboard/activity'),
  getRiskDistribution: () => api.get('/dashboard/risk-distribution'),
  
  // Scenarios
  getScenarios: () => api.get('/scenarios'),
  runScenario: (scenarioId: string, params?: Record<string, any>) => 
    api.post(`/scenarios/${scenarioId}/run`, params || {}),
  getScenarioRuns: () => api.get('/scenarios/runs'),
  
  // Investigations
  getInvestigations: () => api.get('/investigations'),
  getInvestigation: (id: string) => api.get(`/investigations/${id}`),
  createInvestigation: (data: any) => api.post('/investigations', data),
  getInvestigationGraph: (id: string) => api.get(`/investigations/${id}/graph`),
  expandInvestigationGraph: (id: string, accountId: string, depth: number = 1) =>
    api.post(`/investigations/${id}/expand`, { account_id: accountId, depth }),
  getInvestigationTimeline: (id: string) => api.get(`/investigations/${id}/timeline`),
  
  // Transactions
  getTransactions: (params?: Record<string, any>) => api.get('/transactions', { params }),
  getTransaction: (id: string) => api.get(`/transactions/${id}`),
  getTransactionLineage: (id: string) => api.get(`/transactions/${id}/lineage`),
  
  // Provenance
  getProvenanceRecords: (params?: Record<string, any>) => api.get('/provenance', { params }),
  getProvenanceTree: (transactionId: string) => api.get(`/provenance/tree/${transactionId}`),
  
  // Alerts
  getAlerts: (params?: Record<string, any>) => api.get('/alerts', { params }),
  getAlert: (id: string) => api.get(`/alerts/${id}`),
  updateAlertStatus: (id: string, status: string, notes?: string) =>
    api.patch(`/alerts/${id}/status`, { status, notes }),
    
  // Normalisation
  getNormalisationStatus: () => api.get('/normalisation/status'),
  getNormalisationErrors: (params?: Record<string, any>) => api.get('/normalisation/errors', { params }),
  
  // Monitoring
  getMonitoringStatus: () => api.get('/monitoring/status'),
  startMonitoring: () => api.post('/monitoring/start'),
  stopMonitoring: () => api.post('/monitoring/stop'),
  
  // Banks
  getBanks: () => api.get('/banks'),

  // System Status & Settings
  getSystemStatus: () => api.get('/system/status'),
  resetScenarioRun: (runId: string) => api.post(`/scenarios/runs/${runId}/reset`),
};

export default api;
