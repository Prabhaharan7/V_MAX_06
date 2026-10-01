import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowDown,
  ArrowUpRight,
  Asterisk,
  Play,
  Activity,
  Sparkles,
  PlusCircle,
  X,
} from "lucide-react";

interface DashboardHeroProps {
  onScrollToTelemetry?: () => void;
}

export const DashboardHero: React.FC<DashboardHeroProps> = ({
  onScrollToTelemetry,
}) => {
  const navigate = useNavigate();
  const [showTutorialModal, setShowTutorialModal] = useState(false);

  const handleScrollDown = () => {
    if (onScrollToTelemetry) {
      onScrollToTelemetry();
    } else {
      const el = document.getElementById("telemetry-dashboard");
      if (el) {
        el.scrollIntoView({ behavior: "smooth" });
      }
    }
  };

  return (
    <section className="relative min-h-fit w-full bg-[#3E4433] text-[#F0EEE6] flex flex-col justify-between p-6 sm:p-8 lg:p-10 rounded-[32px] overflow-hidden select-none mb-8 border border-[#B9C2A8]/20 shadow-2xl">
      {/* Organic Subtle Grain / Texture Overlay */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-30 mix-blend-overlay"
        style={{
          backgroundImage: `radial-gradient(#F0EEE6 0.75px, transparent 0.75px)`,
          backgroundSize: "24px 24px"
        }}
      />

      {/* Subtle Warm Ambient Glow */}
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-[#7C8A6E]/30 blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 -right-32 w-[30rem] h-[30rem] rounded-full bg-[#E8763A]/15 blur-3xl pointer-events-none" />

      {/* ================= 1. TOP NAV BAR ================= */}
      <nav className="relative z-20 flex items-center justify-between w-full max-w-7xl mx-auto py-2">
        {/* Left: Serif Brand Logo */}
        <Link 
          to="/dashboard" 
          className="font-serif font-bold text-2xl lg:text-3xl tracking-tight text-white hover:text-[#F0EEE6] transition-colors"
        >
          SIF Sentinel<span className="text-[#E8763A]">.</span>
        </Link>

        {/* Center: Pill-shaped Nav Links */}
        <div className="hidden md:flex items-center space-x-1.5 bg-[#1A1F17]/40 backdrop-blur-md border border-[#B9C2A8]/20 rounded-full px-3 py-1.5 shadow-inner">
          <Link
            to="/dashboard"
            className="px-4 py-1.5 text-xs lg:text-sm font-medium rounded-full bg-[#F0EEE6] text-[#1A1F17] transition-all shadow-sm"
          >
            Dashboard
          </Link>
          <Link
            to="/submit"
            className="px-4 py-1.5 text-xs lg:text-sm font-medium rounded-full text-[#F0EEE6] hover:bg-white/10 transition-all"
          >
            Reports
          </Link>
          <Link
            to="/review-queue"
            className="px-4 py-1.5 text-xs lg:text-sm font-medium rounded-full text-[#F0EEE6] hover:bg-white/10 transition-all flex items-center gap-1.5"
          >
            <span>Review Queue</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#E8763A]" />
          </Link>
          <Link
            to="/sites"
            className="px-4 py-1.5 text-xs lg:text-sm font-medium rounded-full text-[#F0EEE6] hover:bg-white/10 transition-all"
          >
            Sites
          </Link>
          <Link
            to="/alerts"
            className="px-4 py-1.5 text-xs lg:text-sm font-medium rounded-full text-[#F0EEE6] hover:bg-white/10 transition-all"
          >
            Alerts
          </Link>
        </div>

        {/* Right: Pill Action Button */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => navigate("/submit")}
            className="bg-[#1A1F17] text-white hover:bg-[#121610] hover:text-[#F0EEE6] text-xs lg:text-sm font-medium px-5 py-2.5 rounded-full border border-white/15 transition-all duration-200 active:scale-95 flex items-center gap-2 shadow-lg"
          >
            <PlusCircle className="w-4 h-4 text-[#E8763A]" />
            <span>New Report</span>
          </button>
        </div>
      </nav>

      {/* ================= 2. LARGE SERIF HEADLINE ================= */}
      <div className="relative z-10 text-center max-w-4xl mx-auto my-auto pt-6 pb-4">
        <h1 className="font-serif font-normal text-3xl sm:text-5xl md:text-6xl lg:text-[68px] leading-[1.08] tracking-tight text-white drop-shadow-sm">
          See the fatal precursor<br className="hidden sm:inline" />{" "}
          before it becomes a statistic
        </h1>
        <p className="mt-3 text-sm md:text-base text-[#F0EEE6]/85 font-sans font-light max-w-xl mx-auto">
          AI-driven intelligence mapping Oil India hazardous energy isolation, lifting, and barrier failures into proactive life-saving interventions.
        </p>
      </div>

      {/* ================= 3. COMPOSITION GRID: CARDS & STATS ================= */}
      <div className="relative z-10 grid grid-cols-1 md:grid-cols-12 gap-6 lg:gap-8 items-end max-w-7xl mx-auto w-full mt-4 pb-2">
        
        {/* === LEFT COLUMN: Seal Badge + Pipeline Texture Card === */}
        <div className="md:col-span-4 flex flex-col justify-between space-y-6">
          {/* Circular Badge/Seal Icon with 2-line caption */}
          <div 
            onClick={handleScrollDown}
            className="flex items-center space-x-3 group cursor-pointer w-fit"
          >
            <div className="w-12 h-12 rounded-full border border-[#B9C2A8]/40 bg-[#1A1F17]/40 backdrop-blur-md flex items-center justify-center text-[#F0EEE6] group-hover:bg-[#1A1F17] group-hover:border-white transition-all duration-300">
              <Activity className="w-5 h-5 text-[#E8763A] group-hover:rotate-12 transition-transform duration-300" />
            </div>
            <div className="text-xs font-sans leading-tight text-[#F0EEE6]/90 font-medium">
              <div>Browse recent</div>
              <div className="text-[#B9C2A8] group-hover:text-white transition-colors">site activity</div>
            </div>
          </div>

          {/* Shorter, Wider Photo Card (Pipeline & Valve detail with floating stat badge) */}
          <div className="relative rounded-[28px] overflow-hidden bg-[#272E23] border border-[#B9C2A8]/25 h-[280px] lg:h-[320px] shadow-xl group">
            {/* High-Fidelity SVG Pipeline Texture Graphic */}
            <svg 
              className="w-full h-full object-cover duotone-sage transition-transform duration-700 group-hover:scale-105" 
              viewBox="0 0 400 280" 
              fill="none" 
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Background gradient */}
              <rect width="400" height="280" fill="#242C20" />
              
              {/* Pipeline cylinder with metallic sheen */}
              <path d="M-20 100 Q 200 80 420 100 L 420 200 Q 200 180 -20 200 Z" fill="#384333" />
              <path d="M-20 120 Q 200 100 420 120 L 420 160 Q 200 140 -20 160 Z" fill="#4B5844" opacity="0.6" />
              
              {/* Flange ring and bolts */}
              <rect x="160" y="70" width="36" height="140" rx="6" fill="#1F261B" stroke="#7C8A6E" strokeWidth="2" />
              <circle cx="178" cy="85" r="5" fill="#B9C2A8" />
              <circle cx="178" cy="115" r="5" fill="#B9C2A8" />
              <circle cx="178" cy="140" r="5" fill="#B9C2A8" />
              <circle cx="178" cy="165" r="5" fill="#B9C2A8" />
              <circle cx="178" cy="195" r="5" fill="#B9C2A8" />

              {/* High-pressure needle valve & dial */}
              <path d="M 280 110 L 280 40 L 300 40 L 300 110 Z" fill="#1A1F17" />
              <circle cx="290" cy="35" r="24" fill="#F0EEE6" stroke="#1A1F17" strokeWidth="3" />
              <circle cx="290" cy="35" r="18" fill="#1A1F17" />
              <path d="M 290 35 L 300 24" stroke="#E8763A" strokeWidth="2.5" strokeLinecap="round" />
              <circle cx="290" cy="35" r="3" fill="#FFFFFF" />

              {/* Texture mesh lines */}
              <path d="M0 60 L400 60 M0 220 L400 220" stroke="#7C8A6E" strokeWidth="1" strokeDasharray="4 4" opacity="0.4" />
            </svg>

            {/* Sage Duotone Treatment Overlay */}
            <div className="absolute inset-0 bg-[#7C8A6E]/30 mix-blend-multiply pointer-events-none" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none" />

            {/* Floating Stat Badge (overlapping bottom-left corner) */}
            <div className="absolute bottom-3 left-3.5 z-20 inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-[#1A1F17]/90 backdrop-blur-md border border-[#B9C2A8]/30 text-white shadow-xl">
              <span className="text-[11px] font-sans text-[#F0EEE6]/80 font-normal">
                Barrier Integrity
              </span>
              <span className="font-serif font-semibold text-lg text-white leading-none">
                82%
              </span>
            </div>
          </div>
        </div>

        {/* === CENTER COLUMN: Tall Photo Card with Amber BG & Dual Overlapping Buttons === */}
        <div className="md:col-span-4 flex justify-center">
          <div className="relative rounded-[28px] overflow-hidden bg-[#E8763A] p-2.5 w-full max-w-[340px] h-[420px] shadow-2xl group flex flex-col justify-between">
            {/* Interior Industrial Photo Graphic Container */}
            <div className="relative w-full h-full rounded-[20px] overflow-hidden bg-[#2A170F]">
              <svg 
                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" 
                viewBox="0 0 320 400" 
                fill="none" 
                xmlns="http://www.w3.org/2000/svg"
              >
                {/* Background Oil Rig Silhouette */}
                <rect width="320" height="400" fill="#2E170A" />
                <path d="M 120 400 L 160 40 L 200 400 Z" fill="#422210" opacity="0.7" />
                <line x1="135" y1="300" x2="185" y2="300" stroke="#E8763A" strokeWidth="2" opacity="0.5" />
                <line x1="145" y1="200" x2="175" y2="200" stroke="#E8763A" strokeWidth="2" opacity="0.5" />
                <line x1="152" y1="120" x2="168" y2="120" stroke="#E8763A" strokeWidth="2" opacity="0.5" />

                {/* Worker Silhouette with Hard Hat & Clipboard Telemetry */}
                <circle cx="160" cy="180" r="22" fill="#FAF9F5" /> {/* Hard Hat */}
                <path d="M 140 180 C 140 166 180 166 180 180 Z" fill="#F2A05C" />
                <circle cx="160" cy="194" r="12" fill="#D7D2C0" /> {/* Face */}
                <path d="M 130 220 C 130 205 190 205 190 220 L 195 360 L 125 360 Z" fill="#FAF9F5" /> {/* Safety Coverall */}
                
                {/* High-Vis Reflective Strips */}
                <rect x="135" y="240" width="50" height="10" fill="#E8763A" rx="2" />
                <rect x="135" y="270" width="50" height="10" fill="#E8763A" rx="2" />

                {/* Lockout / Tagout Badge on equipment */}
                <rect x="200" y="230" width="56" height="80" rx="6" fill="#B23A2E" stroke="#FFFFFF" strokeWidth="1.5" />
                <circle cx="228" cy="242" r="3" fill="#FFFFFF" />
                <rect x="208" y="254" width="40" height="4" fill="#FFFFFF" />
                <rect x="212" y="264" width="32" height="3" fill="#FFFFFF" opacity="0.8" />
                <rect x="212" y="272" width="32" height="3" fill="#FFFFFF" opacity="0.8" />
                <rect x="212" y="280" width="24" height="3" fill="#FFFFFF" opacity="0.8" />
                <path d="M 228 230 L 228 215" stroke="#FFFFFF" strokeWidth="2" />
              </svg>

              {/* Amber Duotone overlay */}
              <div className="absolute inset-0 bg-[#E8763A]/25 mix-blend-multiply pointer-events-none" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/20 pointer-events-none" />

              {/* Card Title / Overlay text */}
              <div className="absolute top-4 left-4 right-4 text-white">
                <span className="text-[10px] font-sans font-medium px-2 py-0.5 rounded-full bg-black/40 backdrop-blur-sm border border-white/20">
                  Critical Barrier Telemetry
                </span>
              </div>
            </div>

            {/* Overlapping Bottom-Left Circular Button Pair (Asterisk + Diagonal Arrow) */}
            <div className="absolute bottom-4 left-4 z-30 flex items-center space-x-2">
              <button
                onClick={() => navigate("/reports/1")}
                title="Explore Safety Standard"
                aria-label="Safety Standard"
                className="w-11 h-11 rounded-full bg-white text-[#1A1F17] flex items-center justify-center shadow-2xl hover:scale-110 active:scale-95 transition-all border border-black/10 focus:outline-none focus:ring-2 focus:ring-amber"
              >
                <Asterisk className="w-5 h-5 text-[#1A1F17]" />
              </button>
              <button
                onClick={() => navigate("/dashboard")}
                title="View Incident Breakdown"
                aria-label="View Incident"
                className="w-11 h-11 rounded-full bg-white text-[#1A1F17] flex items-center justify-center shadow-2xl hover:scale-110 active:scale-95 transition-all border border-black/10 focus:outline-none focus:ring-2 focus:ring-amber"
              >
                <ArrowUpRight className="w-5 h-5 text-[#1A1F17] stroke-[2.2]" />
              </button>
            </div>
          </div>
        </div>

        {/* === RIGHT COLUMN: Circular Dark Graphic + Tutorial Pill + Dual Stats === */}
        <div className="md:col-span-4 flex flex-col justify-between space-y-6 lg:pl-4">
          {/* Circular Dark Stat Graphic with overlapping "Watch Tutorial" Pill */}
          <div className="relative w-44 h-44 mx-auto md:mr-0 md:ml-auto rounded-full bg-[#1A1F17] border border-[#B9C2A8]/30 flex items-center justify-center shadow-xl">
            {/* Subtle Radar Ring Graphic */}
            <svg className="w-full h-full absolute inset-0 text-[#7C8A6E]/30" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="44" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="3 3" />
              <circle cx="50" cy="50" r="32" fill="none" stroke="currentColor" strokeWidth="1" />
              <circle cx="50" cy="50" r="18" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="2 2" />
              <circle cx="50" cy="50" r="4" fill="#E8763A" />
              {/* Radar beam line */}
              <line x1="50" y1="50" x2="80" y2="20" stroke="#E8763A" strokeWidth="1.5" opacity="0.8" />
            </svg>

            {/* Overlapping "Watch Tutorial" Play Button Pill */}
            <button
              onClick={() => setShowTutorialModal(true)}
              className="relative z-10 inline-flex items-center gap-2 bg-[#F0EEE6] hover:bg-white text-[#1A1F17] text-xs font-semibold px-4 py-2 rounded-full shadow-lg hover:scale-105 active:scale-95 transition-all"
            >
              <div className="w-4 h-4 rounded-full bg-[#E8763A] text-white flex items-center justify-center">
                <Play className="w-2.5 h-2.5 fill-current ml-0.5" />
              </div>
              <span>Watch Tutorial</span>
            </button>
          </div>

          {/* Large Stat Numbers Side by Side */}
          <div className="grid grid-cols-2 gap-4 pt-2 border-t border-[#B9C2A8]/20">
            <div>
              <div className="font-serif font-bold text-3xl lg:text-4xl text-white tracking-tight leading-none">
                12.4k+
              </div>
              <div className="font-sans text-xs text-[#B9C2A8] mt-1">
                Reports Analyzed
              </div>
            </div>

            <div>
              <div className="font-serif font-bold text-3xl lg:text-4xl text-[#F2A05C] tracking-tight leading-none">
                340+
              </div>
              <div className="font-sans text-xs text-[#B9C2A8] mt-1">
                SIF-Potential Flagged
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* ================= 4. BOTTOM-RIGHT CORNER SCROLL BUTTON ================= */}
      <div className="absolute bottom-6 right-6 lg:bottom-10 lg:right-10 z-30">
        <button
          onClick={handleScrollDown}
          aria-label="Scroll down to telemetry dashboard"
          className="w-12 h-12 rounded-full bg-white text-[#1A1F17] flex items-center justify-center shadow-2xl hover:scale-110 active:scale-95 transition-all duration-300 group border border-white/40"
        >
          <ArrowDown className="w-5 h-5 text-[#1A1F17] group-hover:translate-y-0.5 transition-transform duration-300 stroke-[2.2]" />
        </button>
      </div>

      {/* Tutorial Video Modal */}
      {showTutorialModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#1A1F17] border border-[#B9C2A8]/30 rounded-3xl max-w-xl w-full p-6 text-[#F0EEE6] relative shadow-2xl animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-[#E8763A]" />
                <h3 className="font-serif text-xl font-medium text-white">
                  SIF Sentinel AI Walkthrough
                </h3>
              </div>
              <button
                onClick={() => setShowTutorialModal(false)}
                className="p-1 rounded-full text-white/70 hover:text-white hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="py-6 space-y-4 text-sm text-[#F0EEE6]/90">
              <p>
                <strong>Welcome to SIF Sentinel AI:</strong> Built for Oil India Limited (SIH 2026 PS 26165).
              </p>
              <ul className="list-disc list-inside space-y-2 text-xs text-[#B9C2A8]">
                <li><strong>NLP Precursor Extraction:</strong> Ingests unstructured incident logs and detects subtle barrier degradation.</li>
                <li><strong>IOGP Rule Matching:</strong> Automatically maps observations to 9 Life-Saving Rules.</li>
                <li><strong>Memory Nearest-Neighbors:</strong> Compares current hazard patterns with historical fatality library cases via dense embeddings.</li>
              </ul>
            </div>

            <div className="flex justify-end pt-4 border-t border-white/10">
              <button
                onClick={() => setShowTutorialModal(false)}
                className="px-5 py-2 rounded-full bg-[#E8763A] text-white text-xs font-semibold hover:bg-[#C55B23] transition-colors"
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
