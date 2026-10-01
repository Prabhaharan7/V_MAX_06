import React, { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth, UserRole } from "../../context/AuthContext";
import {
  LayoutDashboard,
  FileSpreadsheet,
  ListTodo,
  AlertTriangle,
  MapPin,
  Map,
  Settings,
  LogOut,
  ShieldCheck,
  Menu,
  X,
  Activity,
  ChevronRight,
  Flame,
} from "lucide-react";

export const AppShell: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const getRoleBadgeStyle = (role?: UserRole) => {
    switch (role) {
      case "hse_officer":
        return "bg-amber/15 text-amber border-amber/30";
      case "site_manager":
        return "bg-sage-600/20 text-cream border-sage-300/30";
      case "admin":
        return "bg-sage-900 text-sage-300 border-sage-600/40";
      default:
        return "bg-charcoal text-cream/70 border-sage-300/20";
    }
  };

  const getRoleLabel = (role?: UserRole) => {
    switch (role) {
      case "hse_officer":
        return "HSE Officer";
      case "site_manager":
        return "Site Manager";
      case "admin":
        return "Admin";
      default:
        return "Operator";
    }
  };

  const navItems = [
    {
      label: "Dashboard",
      path: "/dashboard",
      icon: LayoutDashboard,
      description: "Precursor density & site rankings",
    },
    {
      label: "Submit Report",
      path: "/submit",
      icon: FileSpreadsheet,
      description: "AI classification & ingestion",
    },
    {
      label: "Review Queue",
      path: "/review-queue",
      icon: ListTodo,
      badge: "Active",
      description: "Active learning triage",
    },
    {
      label: "Risk Map",
      path: "/map",
      icon: Map,
      description: "Geospatial 30d risk forecast",
    },
    {
      label: "Alerts",
      path: "/alerts",
      icon: AlertTriangle,
      description: "Critical barrier spikes",
    },
    {
      label: "Sites",
      path: "/sites",
      icon: MapPin,
      description: "Telemetry & SII scores",
    },
    {
      label: "Settings",
      path: "/settings",
      icon: Settings,
      description: "Thresholds & model config",
    },
  ];

  return (
    <div className="h-screen w-screen overflow-hidden bg-[#1A1F17] text-[#F0EEE6] font-sans selection:bg-amber/30 selection:text-cream grid grid-cols-1 md:grid-cols-[72px_1fr] lg:grid-cols-[280px_1fr]">
      {/* ================= 1. FIXED LEFT SIDEBAR (Desktop >=1280px & Tablet 768-1024px) ================= */}
      <aside className="h-screen bg-[#151912] border-r border-sage-300/15 hidden md:flex flex-col justify-between overflow-y-auto z-40 shrink-0 p-3 lg:p-5">
        <div className="space-y-6">
          {/* Logo / Brand Header */}
          <div className="flex items-center space-x-3 px-1 lg:px-2 pt-1">
            <div className="w-10 h-10 rounded-2xl bg-sage-900 border border-sage-300/30 flex items-center justify-center text-amber shadow-sm shrink-0">
              <Flame className="w-5 h-5" />
            </div>
            <div className="hidden lg:block min-w-0">
              <div className="flex items-center space-x-1.5">
                <span className="font-serif font-bold text-lg tracking-tight text-white truncate">
                  SIF Sentinel
                </span>
                <span className="text-[10px] font-sans font-medium px-1.5 py-0.5 rounded-full bg-sage-900 text-sage-300 border border-sage-600/30 shrink-0">
                  OIL
                </span>
              </div>
              <p className="text-[11px] text-sage-300 font-sans truncate">
                Oil India PS-26165
              </p>
            </div>
          </div>

          {/* Operational Control Room Tag (Desktop only) */}
          <div className="hidden lg:flex px-3.5 py-2.5 rounded-2xl bg-sage-900/40 border border-sage-300/20 items-center space-x-3">
            <ShieldCheck className="w-4 h-4 text-amber shrink-0" />
            <div className="text-xs min-w-0">
              <div className="font-serif font-medium text-cream truncate">Control Room</div>
              <div className="text-sage-300 text-[10px] truncate">Assam & Rajasthan Ops</div>
            </div>
          </div>

          {/* Navigation Items */}
          <nav className="space-y-1">
            <div className="hidden lg:block text-[11px] font-sans font-medium text-sage-300 px-3 mb-2 uppercase tracking-wider">
              Operational Modules
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                location.pathname === item.path ||
                (item.path === "/dashboard" && location.pathname === "/");

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  title={item.label}
                  className={`flex items-center justify-between rounded-full text-xs font-medium transition-all group ${
                    isActive
                      ? "bg-[#3E4433] text-[#F0EEE6] border border-sage-300/30"
                      : "text-sage-300 hover:text-white hover:bg-sage-900/50"
                  } p-2.5 lg:px-4 lg:py-2.5`}
                >
                  <div className="flex items-center space-x-3 mx-auto lg:mx-0">
                    <Icon
                      className={`w-4 h-4 shrink-0 ${
                        isActive ? "text-amber" : "text-sage-300 group-hover:text-cream"
                      }`}
                    />
                    <span className="hidden lg:inline font-sans text-sm">{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="hidden lg:inline text-[9px] font-sans px-2 py-0.5 rounded-full bg-amber/20 text-amber border border-amber/30">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Telemetry Summary / Status at sidebar bottom */}
        <div className="hidden lg:block p-3.5 rounded-2xl bg-sage-900/40 border border-sage-300/15 text-xs space-y-2 text-sage-300">
          <div className="flex items-center justify-between text-cream font-medium">
            <span className="flex items-center space-x-1.5">
              <Activity className="w-3.5 h-3.5 text-amber" />
              <span className="font-serif text-xs">AI Classifier</span>
            </span>
            <span className="text-emerald-400 text-[10px] font-mono">v1.2 Active</span>
          </div>
          <div className="flex justify-between border-t border-sage-300/15 pt-1.5 text-[11px]">
            <span>90d Window:</span>
            <span className="text-cream">Continuous</span>
          </div>
          <div className="flex justify-between text-[11px]">
            <span>IOGP Rules:</span>
            <span className="text-cream">9 Standards</span>
          </div>
        </div>
      </aside>

      {/* ================= 2. MOBILE NAVIGATION DRAWER (<768px) ================= */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden bg-black/80 backdrop-blur-sm flex">
          <div className="w-72 bg-[#151912] border-r border-sage-300/20 p-5 flex flex-col justify-between h-full animate-in slide-in-from-left duration-200">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-sage-300/20">
                <div className="flex items-center space-x-2.5">
                  <Flame className="w-5 h-5 text-amber" />
                  <span className="font-serif font-medium text-lg text-cream">SIF Sentinel</span>
                </div>
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-1 rounded-full text-sage-300 hover:text-white"
                  aria-label="Close menu"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <nav className="space-y-1.5">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive =
                    location.pathname === item.path ||
                    (item.path === "/dashboard" && location.pathname === "/");
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center justify-between px-4 py-2.5 rounded-full text-sm font-medium transition ${
                        isActive
                          ? "bg-[#3E4433] text-white border border-sage-300/30"
                          : "text-sage-300 hover:text-white hover:bg-sage-900/50"
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <Icon className="w-4 h-4 text-amber" />
                        <span>{item.label}</span>
                      </div>
                      <ChevronRight className="w-4 h-4 text-sage-300" />
                    </NavLink>
                  );
                })}
              </nav>
            </div>

            <button
              onClick={() => {
                setMobileMenuOpen(false);
                logout();
              }}
              className="w-full py-2.5 px-4 rounded-full bg-critical/15 border border-critical/30 text-cream flex items-center justify-center space-x-2 text-sm font-medium hover:bg-critical/25 transition"
            >
              <LogOut className="w-4 h-4" />
              <span>Sign Out</span>
            </button>
          </div>
          <div className="flex-1" onClick={() => setMobileMenuOpen(false)} />
        </div>
      )}

      {/* ================= 3. MAIN CONTENT COLUMN ================= */}
      <div className="flex flex-col h-screen min-w-0 overflow-hidden">
        {/* ================= SOLID 72PX TOP BAR (position: sticky; top: 0; z-index: 50) ================= */}
        <header className="h-[72px] min-h-[72px] max-h-[72px] border-b border-sage-300/15 bg-[#151912] sticky top-0 z-50 flex items-center justify-between px-4 sm:px-6 lg:px-12 shrink-0">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-full text-cream/70 hover:text-white hover:bg-sage-900 md:hidden"
              aria-label="Toggle Navigation"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            <div className="flex items-center space-x-3">
              <span className="font-serif font-semibold text-lg lg:text-xl tracking-tight text-white truncate">
                SIF Sentinel AI
              </span>
              <span className="hidden sm:inline text-xs font-sans px-2.5 py-0.5 rounded-full bg-sage-900 text-sage-300 border border-sage-600/30 shrink-0">
                Oil India Intelligence
              </span>
            </div>
          </div>

          {/* Telemetry Indicator & User Account Controls */}
          <div className="flex items-center space-x-4 sm:space-x-6">
            <div className="hidden sm:flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-sage-900 border border-sage-300/20 text-cream text-xs shrink-0">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber"></span>
              </span>
              <span className="font-sans">NLP Pipeline Active</span>
            </div>

            {user && (
              <div className="flex items-center space-x-3 sm:space-x-4 border-l border-sage-300/15 pl-4 sm:pl-6 shrink-0">
                <div className="text-right hidden md:block min-w-0">
                  <div className="text-xs font-medium text-cream truncate max-w-[140px]">{user.name}</div>
                  <div className="text-[11px] text-sage-300 truncate max-w-[140px]">{user.email}</div>
                </div>
                <span
                  className={`text-[11px] font-sans font-medium px-2.5 py-0.5 rounded-full border shrink-0 ${getRoleBadgeStyle(
                    user.role
                  )}`}
                >
                  {getRoleLabel(user.role)}
                </span>

                <button
                  onClick={logout}
                  title="Sign Out"
                  className="p-2 rounded-full text-sage-300 hover:text-white hover:bg-sage-900 transition border border-transparent hover:border-sage-300/20 focus:outline-none focus:ring-2 focus:ring-amber/50"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </header>

        {/* ================= 4. INDEPENDENT SCROLL CONTAINER (height: calc(100vh - 72px)) ================= */}
        <main className="flex-1 h-[calc(100vh-72px)] overflow-y-auto bg-[#1A1F17]">
          <div className="max-w-[1400px] w-full mx-auto px-4 sm:px-6 lg:px-12 py-8 space-y-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
