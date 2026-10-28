import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Landmark, 
  Cpu, 
  ArrowLeftRight, 
  Search, 
  GitFork, 
  ShieldAlert, 
  Database, 
  Settings 
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/banks', label: 'Bank Network', icon: Landmark },
    { to: '/scenarios', label: 'Scenario Simulator', icon: Cpu },
    { to: '/transactions', label: 'Transaction Monitor', icon: ArrowLeftRight },
    { to: '/investigation', label: 'Investigations', icon: Search },
    { to: '/provenance', label: 'Provenance Explorer', icon: GitFork },
    { to: '/alerts', label: 'Alerts & Cases', icon: ShieldAlert },
    { to: '/normalisation', label: 'Data & Audit', icon: Database },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="mm-sidebar">
      <div className="mm-sidebar-header">
        <div className="mm-sidebar-brand">
          <span className="mm-brand-title">MULE MATRIX</span>
          <span className="mm-brand-tagline">Follow the Money. Uncover the Network.</span>
        </div>
      </div>

      <nav className="mm-sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `mm-nav-item ${isActive ? 'active' : ''}`}
              end={item.to === '/'}
            >
              <Icon className="mm-nav-icon" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
};
