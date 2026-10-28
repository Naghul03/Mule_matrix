import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { BankNetworkView } from './pages/BankNetworkView';
import { ScenariosView } from './pages/ScenariosView';
import { TransactionsView } from './pages/TransactionsView';
import { InvestigationView } from './pages/InvestigationView';
import { ProvenanceExplorer } from './pages/ProvenanceExplorer';
import { AlertsView } from './pages/AlertsView';
import { NormalisationView } from './pages/NormalisationView';
import { SettingsView } from './pages/SettingsView';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <div className="mm-main-area">
          <Header />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/banks" element={<BankNetworkView />} />
            <Route path="/scenarios" element={<ScenariosView />} />
            <Route path="/transactions" element={<TransactionsView />} />
            <Route path="/investigation" element={<InvestigationView />} />
            <Route path="/provenance" element={<ProvenanceExplorer />} />
            <Route path="/alerts" element={<AlertsView />} />
            <Route path="/normalisation" element={<NormalisationView />} />
            <Route path="/settings" element={<SettingsView />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
};

export default App;
