import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  Flame,
  ShieldCheck,
  Lock,
  Mail,
  AlertCircle,
  Activity,
  ArrowRight,
  HardHat,
  Cpu,
} from "lucide-react";

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("pranab.hse@oilindia.in");
  const [password, setPassword] = useState("OilIndia@2026");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // If already authenticated, redirect
  React.useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as any)?.from?.pathname || "/dashboard";
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const result = await login(email, password);
    setIsSubmitting(false);

    if (result.success) {
      const from = (location.state as any)?.from?.pathname || "/dashboard";
      navigate(from, { replace: true });
    } else {
      setError(result.error || "Login failed. Please verify your credentials.");
    }
  };

  const handlePersonaSelect = (personaEmail: string, personaPass: string) => {
    setEmail(personaEmail);
    setPassword(personaPass);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-[#060a12] text-slate-100 flex flex-col justify-center items-center p-4 relative overflow-hidden font-sans">
      {/* Background ambient lighting effects */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-red-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-900/5 rounded-full blur-3xl pointer-events-none" />

      {/* Grid overlay */}
      <div 
        className="absolute inset-0 opacity-[0.03] pointer-events-none" 
        style={{
          backgroundImage: "linear-gradient(#ffffff 1px, transparent 1px), linear-gradient(90deg, #ffffff 1px, transparent 1px)",
          backgroundSize: "40px 40px"
        }}
      />

      <div className="w-full max-w-4xl grid lg:grid-cols-12 gap-8 items-center relative z-10">
        {/* Left Side: System Narrative & Oil India Context */}
        <div className="lg:col-span-6 space-y-6 hidden lg:block">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-mono font-semibold">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
            </span>
            <span>SIH 2026 • PS-26165 AI PLATFORM</span>
          </div>

          <div className="space-y-2">
            <h1 className="text-3xl font-black tracking-tight text-white flex items-center space-x-3">
              <span>SIF Sentinel AI</span>
            </h1>
            <p className="text-sm text-slate-300 font-normal leading-relaxed">
              Industrial AI & NLP Precursor Intelligence Platform detecting Serious Injury & Fatality (SIF) precursors across Oil India Limited operational assets.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1 backdrop-blur-sm">
              <div className="flex items-center space-x-2 text-amber-400">
                <HardHat className="w-4 h-4" />
                <span className="text-xs font-mono font-bold">9 IOGP LSR</span>
              </div>
              <p className="text-[11px] text-slate-400">Automated multi-label tagging & barrier failure mapping</p>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1 backdrop-blur-sm">
              <div className="flex items-center space-x-2 text-cyan-400">
                <Cpu className="w-4 h-4" />
                <span className="text-xs font-mono font-bold">pgvector 384d</span>
              </div>
              <p className="text-[11px] text-slate-400">Semantic Safety Memory & historical case matching</p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80 text-xs text-slate-400 font-mono flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <span>Assam, Rajasthan & KG Basin Rigs</span>
            </div>
            <span className="text-emerald-400">100% ONLINE</span>
          </div>
        </div>

        {/* Right Side: Industrial Dark Login Card */}
        <div className="lg:col-span-6 w-full max-w-md mx-auto">
          <div className="bg-[#0e1626]/90 border border-slate-800/90 rounded-2xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl relative">
            {/* Header / Brand */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-red-600 flex items-center justify-center shadow-lg shadow-amber-950/50 border border-amber-400/40">
                  <Flame className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white tracking-wide">Control Room Login</h2>
                  <p className="text-xs text-slate-400 font-mono">Secure Enterprise Portal</p>
                </div>
              </div>
              <ShieldCheck className="w-6 h-6 text-slate-600" />
            </div>

            {/* Error Notification */}
            {error && (
              <div className="mb-5 p-3 rounded-lg bg-red-950/50 border border-red-500/40 text-red-300 text-xs flex items-start space-x-2.5 animate-in fade-in slide-in-from-top-2">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5 uppercase tracking-wider">
                  Operational Email
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="officer@oilindia.in"
                    className="w-full pl-9 pr-3 py-2.5 bg-slate-950/70 border border-slate-800 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 rounded-lg text-sm text-white placeholder-slate-600 transition outline-none font-mono"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-mono font-medium text-slate-300 uppercase tracking-wider">
                    Password
                  </label>
                  <span className="text-[10px] text-slate-500 font-mono">Bcrypt Encrypted</span>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-3 py-2.5 bg-slate-950/70 border border-slate-800 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 rounded-lg text-sm text-white placeholder-slate-600 transition outline-none font-mono"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full mt-2 py-3 px-4 bg-gradient-to-r from-amber-500 hover:from-amber-400 to-amber-600 text-slate-950 font-bold text-sm rounded-lg shadow-lg shadow-amber-950/40 hover:shadow-amber-500/20 transition flex items-center justify-center space-x-2 disabled:opacity-50 cursor-pointer"
              >
                {isSubmitting ? (
                  <div className="w-5 h-5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Authenticate Session</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Quick Persona Switcher for Evaluation */}
            <div className="mt-6 pt-5 border-t border-slate-800/80">
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-2.5 text-center">
                Fast Demo Persona Switcher
              </div>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => handlePersonaSelect("pranab.hse@oilindia.in", "OilIndia@2026")}
                  className="p-2 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-left transition group"
                >
                  <div className="text-[10px] font-mono font-bold text-amber-400">HSE Officer</div>
                  <div className="text-[9px] text-slate-400 truncate">Pranab P.</div>
                </button>

                <button
                  type="button"
                  onClick={() => handlePersonaSelect("arun.manager@oilindia.in", "OilIndia@2026")}
                  className="p-2 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-left transition group"
                >
                  <div className="text-[10px] font-mono font-bold text-cyan-400">Site Manager</div>
                  <div className="text-[9px] text-slate-400 truncate">Arun Borah</div>
                </button>

                <button
                  type="button"
                  onClick={() => handlePersonaSelect("admin@oilindia.in", "Admin@2026")}
                  className="p-2 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-left transition group"
                >
                  <div className="text-[10px] font-mono font-bold text-emerald-400">Admin</div>
                  <div className="text-[9px] text-slate-400 truncate">HQ Admin</div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
