import { useState } from "react";

import { AdminShell } from "./layouts/AdminShell";
import { UserShell } from "./layouts/UserShell";
import { AppMode, AdminViewId, UserViewId } from "./lib/navigation";
import { useDashboard } from "./lib/useDashboard";

import { UserHomeView } from "./views/user/UserHomeView";
import { UserDocumentUploadView } from "./views/user/UserDocumentUploadView";
import { UserLiveFilterView } from "./views/user/UserLiveFilterView";
import { UserPrivacyView } from "./views/user/UserPrivacyView";
import { UserHowItWorksView } from "./views/user/UserHowItWorksView";

import { AdminOverviewView } from "./views/admin/AdminOverviewView";
import { OperationalZoneView } from "./views/admin/OperationalZoneView";
import { SovereignVaultView } from "./views/admin/SovereignVaultView";
import { AdminAccessView } from "./views/admin/AdminAccessView";
import { AuditLogView } from "./views/admin/AuditLogView";
import { MetricsView } from "./views/admin/MetricsView";

import "./multi-select.css";

export default function App() {
  const [appMode, setAppMode] = useState<AppMode>("user");
  const [activeUserView, setActiveUserView] = useState<UserViewId>("home");
  const [activeAdminView, setActiveAdminView] = useState<AdminViewId>("overview");

  const { dashboard, isLoading, refreshDashboard } = useDashboard();

  const records = dashboard.storageRecords.data?.records ?? [];
  const latestRecordId = String(records[0]?.record_id ?? "");

  if (appMode === "user") {
    // The live filter view stays mounted (display-toggled) so an active
    // backend camera session is not torn down while navigating within user mode.
    const renderActiveUserView = () => {
      switch (activeUserView) {
        case "home":
          return <UserHomeView onNavigate={setActiveUserView} />;
        case "document-upload":
          return (
            <UserDocumentUploadView
              redactionConfig={dashboard.redactionConfig.data ?? null}
              onRefresh={refreshDashboard}
            />
          );
        case "privacy":
          return <UserPrivacyView />;
        case "how-it-works":
          return <UserHowItWorksView onNavigate={setActiveUserView} />;
        case "live-filter":
          return null;
        default:
          return <UserHomeView onNavigate={setActiveUserView} />;
      }
    };

    return (
      <UserShell
        appMode={appMode}
        onModeChange={setAppMode}
        activeView={activeUserView}
        onNavigate={setActiveUserView}
      >
        {activeUserView !== "live-filter" && renderActiveUserView()}
        <div style={{ display: activeUserView === "live-filter" ? "" : "none" }}>
          <UserLiveFilterView isActive={activeUserView === "live-filter"} />
        </div>
      </UserShell>
    );
  }

  const renderAdminView = () => {
    switch (activeAdminView) {
      case "overview":
        return (
          <AdminOverviewView dashboard={dashboard} records={records} onNavigate={setActiveAdminView} />
        );
      case "operational-zone":
        return <OperationalZoneView recordsResult={dashboard.storageRecords} />;
      case "sovereign-vault":
        return <SovereignVaultView records={records} keyInfo={dashboard.cryptoKeyInfo} />;
      case "admin-access":
        return <AdminAccessView latestRecordId={latestRecordId} />;
      case "audit-log":
        return <AuditLogView initialLogs={dashboard.auditLogs} />;
      case "metrics":
        return <MetricsView dashboard={dashboard} />;
      default:
        return (
          <AdminOverviewView dashboard={dashboard} records={records} onNavigate={setActiveAdminView} />
        );
    }
  };

  return (
    <AdminShell
      appMode={appMode}
      onModeChange={setAppMode}
      activeView={activeAdminView}
      onNavigate={setActiveAdminView}
      online={dashboard.health.ok}
      isLoading={isLoading}
      onRefresh={refreshDashboard}
    >
      {renderAdminView()}
    </AdminShell>
  );
}
