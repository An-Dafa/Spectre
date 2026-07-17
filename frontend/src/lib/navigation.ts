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
  SlidersHorizontal,
  Video,
} from "lucide-react";
import { createElement, ReactNode } from "react";

export type AppMode = "user" | "government";

export type UserViewId = "home" | "document-upload" | "live-filter" | "privacy" | "how-it-works";

export type GovernmentViewId =
  | "overview"
  | "operational-zone"
  | "sovereign-vault"
  | "government-access"
  | "dynamic-injection"
  | "audit-log"
  | "metrics";

export type NavItem<T extends string> = {
  id: T;
  label: string;
  icon: ReactNode;
  description: string;
};

export const userNavItems: NavItem<UserViewId>[] = [
  { id: "home", label: "Home", icon: createElement(Home, { size: 18 }), description: "Beranda Spectre" },
  { id: "privacy", label: "Privacy", icon: createElement(ShieldCheck, { size: 18 }), description: "Privacy-first flow" },
  { id: "how-it-works", label: "How It Works", icon: createElement(Gauge, { size: 18 }), description: "Langkah demi langkah" },
];

export const governmentNavItems: NavItem<GovernmentViewId>[] = [
  { id: "overview", label: "Overview", icon: createElement(Gauge, { size: 20 }), description: "Ringkasan console" },
  { id: "operational-zone", label: "Operational Zone", icon: createElement(Database, { size: 20 }), description: "Data tersensor" },
  { id: "sovereign-vault", label: "Sovereign Vault", icon: createElement(LockKeyhole, { size: 20 }), description: "Penyimpanan asli" },
  { id: "government-access", label: "Government Access", icon: createElement(Landmark, { size: 20 }), description: "Otorisasi original" },
  { id: "dynamic-injection", label: "Dynamic Injection", icon: createElement(SlidersHorizontal, { size: 20 }), description: "Runtime policy" },
  { id: "audit-log", label: "Audit Log", icon: createElement(Activity, { size: 20 }), description: "Jejak keamanan" },
  { id: "metrics", label: "Metrics", icon: createElement(FileText, { size: 20 }), description: "Ringkasan sistem" },
];

// Live filter is reachable from the user Home tools section, not the top nav.
export const userToolViewIds = {
  documentUpload: "document-upload" as UserViewId,
  liveFilter: "live-filter" as UserViewId,
};

export const liveNavIcon = createElement(Video, { size: 18 });
