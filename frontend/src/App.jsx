import { useState } from 'react';

import { GovernmentShell } from './layouts/GovernmentShell';
import { UserShell } from './layouts/UserShell';
import { useDashboard } from './lib/useDashboard';

import { UserHomeView } from './views/user/UserHomeView';
import { UserDocumentUploadView } from './views/user/UserDocumentUploadView';
import { UserLiveFilterView } from './views/user/UserLiveFilterView';
import { UserPrivacyView } from './views/user/UserPrivacyView';
import { UserHowItWorksView } from './views/user/UserHowItWorksView';

import { GovernmentOverviewView } from './views/government/GovernmentOverviewView';
import { OperationalZoneView } from './views/government/OperationalZoneView';
import { SovereignVaultView } from './views/government/SovereignVaultView';
import { GovernmentAccessView } from './views/government/GovernmentAccessView';
import { DynamicInjectionView } from './views/government/DynamicInjectionView';
import { AuditLogView } from './views/government/AuditLogView';
import { MetricsView } from './views/government/MetricsView';

import './multi-select.css';
import './workbench.css';

function detectMode(identity) {
  return /admin|operator|government|gov/i.test(identity) ? 'government' : 'user';
}

export default function App() {
  const [session, setSession] = useState(null);
  const [activeUserView, setActiveUserView] = useState('home');
  const [activeGovernmentView, setActiveGovernmentView] = useState('overview');
  const { dashboard, isLoading, refreshDashboard } = useDashboard();

  if (!session) {
    return <SignInView onSignIn={setSession} />;
  }

  const records = dashboard.storageRecords.data?.records ?? [];
  const latestRecordId = String(records[0]?.record_id ?? '');

  function setAppMode(mode) {
    setSession((current) => ({ ...current, mode }));
  }

  if (session.mode === 'user') {
    const renderActiveUserView = () => {
      switch (activeUserView) {
        case 'home':
          return <UserHomeView onNavigate={setActiveUserView} />;
        case 'document-upload':
          return <UserDocumentUploadView redactionConfig={dashboard.redactionConfig.data ?? null} onRefresh={refreshDashboard} />;
        case 'privacy':
          return <UserPrivacyView />;
        case 'how-it-works':
          return <UserHowItWorksView onNavigate={setActiveUserView} />;
        case 'live-filter':
          return null;
        default:
          return <UserHomeView onNavigate={setActiveUserView} />;
      }
    };

    return (
      <UserShell appMode={session.mode} onModeChange={setAppMode} activeView={activeUserView} onNavigate={setActiveUserView}>
        {activeUserView !== 'live-filter' && renderActiveUserView()}
        <div style={{ display: activeUserView === 'live-filter' ? '' : 'none' }}>
          <UserLiveFilterView isActive={activeUserView === 'live-filter'} />
        </div>
      </UserShell>
    );
  }

  const renderGovernmentView = () => {
    switch (activeGovernmentView) {
      case 'overview':
        return <GovernmentOverviewView dashboard={dashboard} records={records} onNavigate={setActiveGovernmentView} />;
      case 'operational-zone':
        return <OperationalZoneView recordsResult={dashboard.storageRecords} />;
      case 'sovereign-vault':
        return <SovereignVaultView records={records} keyInfo={dashboard.cryptoKeyInfo} />;
      case 'government-access':
        return <GovernmentAccessView latestRecordId={latestRecordId} />;
      case 'dynamic-injection':
        return <DynamicInjectionView redactionConfig={dashboard.redactionConfig.data ?? null} onRefresh={refreshDashboard} />;
      case 'audit-log':
        return <AuditLogView initialLogs={dashboard.auditLogs} />;
      case 'metrics':
        return <MetricsView dashboard={dashboard} />;
      default:
        return <GovernmentOverviewView dashboard={dashboard} records={records} onNavigate={setActiveGovernmentView} />;
    }
  };

  return (
    <GovernmentShell
      appMode={session.mode}
      onModeChange={setAppMode}
      activeView={activeGovernmentView}
      onNavigate={setActiveGovernmentView}
      online={dashboard.health.ok}
      isLoading={isLoading}
      onRefresh={refreshDashboard}
    >
      {renderGovernmentView()}
    </GovernmentShell>
  );
}

function SignInView({ onSignIn }) {
  const [identity, setIdentity] = useState('user@spectre.local');

  function submit(event) {
    event.preventDefault();
    onSignIn({ identity, mode: detectMode(identity) });
  }

  return (
    <main className="signin-page min-h-screen">
      <form className="signin-card" onSubmit={submit}>
        <div className="signin-logo">S</div>
        <p className="eyebrow">Spectre Workspace</p>
        <h1>Masuk ke panel kerja</h1>
        <p>
          Masukkan identitas. Akun biasa masuk ke panel user; identitas admin/operator masuk ke panel operator.
        </p>
        <label>
          Email / role
          <input value={identity} onChange={(event) => setIdentity(event.target.value)} placeholder="operator@spectre.local" />
        </label>
        <button type="submit">Sign in</button>
        <div className="signin-shortcuts">
          <button type="button" onClick={() => onSignIn({ identity: 'user@spectre.local', mode: 'user' })}>User demo</button>
          <button type="button" onClick={() => onSignIn({ identity: 'operator@spectre.local', mode: 'government' })}>Operator demo</button>
        </div>
      </form>
    </main>
  );
}
