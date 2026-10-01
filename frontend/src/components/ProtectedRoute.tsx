import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth, UserRole } from "../context/AuthContext";
import { ShieldAlert } from "lucide-react";

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles,
}) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-300">
        <div className="relative w-16 h-16 flex items-center justify-center mb-4">
          <div className="absolute inset-0 rounded-full border-2 border-amber-500/30 animate-ping"></div>
          <div className="w-12 h-12 rounded-full border-2 border-t-amber-500 border-r-transparent border-b-amber-500 border-l-transparent animate-spin"></div>
          <ShieldAlert className="w-6 h-6 text-amber-500 absolute" />
        </div>
        <p className="text-sm font-mono tracking-widest text-slate-400 uppercase">
          Authenticating SIF Sentinel Session...
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6 text-slate-100">
        <div className="max-w-md w-full bg-slate-900/90 border border-red-500/30 rounded-xl p-8 text-center shadow-2xl backdrop-blur-xl">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center">
            <ShieldAlert className="w-8 h-8 text-red-500" />
          </div>
          <h2 className="text-xl font-bold tracking-tight text-white mb-2">Access Restricted</h2>
          <p className="text-sm text-slate-400 mb-6">
            Your current role (<span className="text-amber-400 font-mono font-semibold uppercase">{user.role}</span>) does not have authorization to view this section.
          </p>
          <button
            onClick={() => window.history.back()}
            className="px-4 py-2 text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 transition"
          >
            Return to Previous Page
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
