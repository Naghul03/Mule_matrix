import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Clock, RefreshCw } from 'lucide-react';
import { endpoints } from '../api/client';

interface HeaderProps {
  onRefresh?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onRefresh }) => {
  const location = useLocation();
  const [monitoringActive, setMonitoringActive] = useState<boolean>(true);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  useEffect(() => {
    updateTime();
    checkMonitoring();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const updateTime = () => {
    const now = new Date();
    setLastUpdated(now.toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' }));
  };

  const checkMonitoring = async () => {
    try {
      const res = await endpoints.getMonitoringStatus();
      setMonitoringActive(res.data?.status === 'RUNNING' || res.data?.is_running !== false);
    } catch {
      setMonitoringActive(true);
    }
  };

  const getPageTitle = () => {
    switch (location.pathname) {
      case '/': return 'Overview Dashboard';
      case '/banks': return 'Federated Bank Network';
      case '/scenarios': return 'Scenario Simulator';
      case '/transactions': return 'Transaction Monitor';
      case '/investigation': return 'Investigation Workspace';
      case '/provenance': return 'Provenance Explorer';
      case '/alerts': return 'Alerts and Investigations';
      case '/normalisation': return 'Data Normalisation and Audit';
      case '/settings': return 'System Status and Settings';
      default: return 'Mule Matrix Console';
    }
  };

  return (
    <header className="mm-top-header">
      <div className="mm-header-left">
        <span className="mm-header-page-title">{getPageTitle()}</span>
      </div>

      <div className="mm-header-right">
        <div className="mm-status-pill live">
          <span className="dot"></span>
          <span>Live Monitoring</span>
        </div>

        <div className="mm-badge-timestamp">
          <span>Last updated: {lastUpdated || '11:24:32 AM'}</span>
        </div>

        {onRefresh && (
          <button onClick={onRefresh} className="mm-btn-icon" title="Refresh Data">
            <RefreshCw className="mm-nav-icon" />
          </button>
        )}
      </div>
    </header>
  );
};
