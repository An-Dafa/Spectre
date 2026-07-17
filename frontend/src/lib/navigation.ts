// Shared navigation types + nav item definitions for both shells.
import {
  Activity,
  Database,
  FileText,
  Gauge,
  Home,
  Landmark,
  LockKeyhole,
  ShieldCheck,
  Video,
} from "lucide-react";
import { createElement, ReactNode } from "react";

export type AppMode = "user" | "admin";

export type UserViewId = "home" | "document-upload" | "live-filter" | "privacy" | "how-it-works";

export type AdminViewId =
  | "overview"
  | "operational-zone"
  | "sovereign-vault"
  | "admin-access"
  | "audit-log"
  | "metrics";

export type NavItem<T extends string> = {
  id: T;
  label: string;
  icon: ReactNode;
  description: string;
};

export const userNavItems: NavItem<UserViewId>[] = [
  { id: "home", label: "Home", icon: createElement(Home, { size: 18 }), description: "Spectre home" },
  { id: "privacy", label: "Privacy", icon: createElement(ShieldCheck, { size: 18 }), description: "Privacy-first flow" },
  { id: "how-it-works", label: "How It Works", icon: createElement(Gauge, { size: 18 }), description: "Step by step" },
];

export const adminNavItems: NavItem<AdminViewId>[] = [
  { id: "overview", label: "Overview", icon: createElement(Gauge, { size: 20 }), description: "Console summary" },
  { id: "operational-zone", label: "Operational Zone", icon: createElement(Database, { size: 20 }), description: "Redacted data" },
  { id: "sovereign-vault", label: "Sovereign Vault", icon: createElement(LockKeyhole, { size: 20 }), description: "Original storage" },
  { id: "admin-access", label: "Admin Access", icon: createElement(Landmark, { size: 20 }), description: "Original authorization" },
  { id: "audit-log", label: "Audit Log", icon: createElement(Activity, { size: 20 }), description: "Security trail" },
  { id: "metrics", label: "Metrics", icon: createElement(FileText, { size: 20 }), description: "System summary" },
];

// Live filter is reachable from the user Home tools section, not the top nav.
export const userToolViewIds = {
  documentUpload: "document-upload" as UserViewId,
  liveFilter: "live-filter" as UserViewId,
};

export const liveNavIcon = createElement(Video, { size: 18 });
