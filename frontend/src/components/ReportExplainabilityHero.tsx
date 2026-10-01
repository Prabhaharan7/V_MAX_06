import React from "react";
import {
  Asterisk,
  ArrowUpRight,
  Sparkles,
  Flame,
  Star,
  CheckCircle2,
} from "lucide-react";

interface ReportExplainabilityHeroProps {
  onExploreExplanation?: () => void;
  onViewLsrDetails?: () => void;
}

export const ReportExplainabilityHero: React.FC<ReportExplainabilityHeroProps> = ({
  onExploreExplanation,
  onViewLsrDetails,
}) => {
  return (
    <section className="relative w-full rounded-[32px] bg-[#E8763A] text-white p-6 sm:p-8 lg:p-12 overflow-hidden shadow-2xl select-none mb-8 border border-white/15">
      {/* Subtle Warm Background Accent Texture */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-20 mix-blend-overlay"
        style={{
          backgroundImage: `radial-gradient(#FFFFFF 0.75px, transparent 0.75px)`,
          backgroundSize: "20px 20px"
        }}
      />
      <div className="absolute -bottom-24 -left-24 w-80 h-80 rounded-full bg-[#C55B23]/40 blur-3xl pointer-events-none" />

      {/* Two-Column Grid */}
      <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
        
        {/* ================= LEFT HALF: Photo & Overlapping Card ================= */}
        <div className="lg:col-span-6 flex justify-center lg:justify-start">
          <div className="relative w-full max-w-[420px]">
            
            {/* Sage-Green Backdrop Block Behind Photo */}
            <div className="bg-[#3E4433] rounded-[32px] p-3 sm:p-4 shadow-xl border border-[#B9C2A8]/25">
              
              {/* Photo Card: Field Worker / HSE Officer Reviewing Tablet */}
              <div className="relative rounded-[24px] overflow-hidden bg-[#272E23] aspect-[4/3.8] group">
                
                {/* High-Fidelity Vector Field Inspection Artwork */}
                <svg
                  className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                  viewBox="0 0 400 380"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  {/* Background Facility & Structure */}
                  <rect width="400" height="380" fill="#2E3729" />
                  <path d="M 40 380 L 100 80 L 140 380 Z" fill="#3D4936" opacity="0.6" />
                  <line x1="60" y1="240" x2="120" y2="240" stroke="#7C8A6E" strokeWidth="2" opacity="0.4" />
                  <line x1="75" y1="160" x2="110" y2="160" stroke="#7C8A6E" strokeWidth="2" opacity="0.4" />

                  {/* Oil Pipeline & Flanges in background */}
                  <path d="M 220 380 L 220 120 L 380 120" stroke="#1F261B" strokeWidth="28" strokeLinecap="round" />
                  <circle cx="340" cy="120" r="18" fill="#E8763A" opacity="0.85" />
                  <circle cx="340" cy="120" r="12" fill="#FFFFFF" />
                  <line x1="340" y1="120" x2="346" y2="114" stroke="#B23A2E" strokeWidth="2" strokeLinecap="round" />

                  {/* HSE Officer Character */}
                  {/* Hard Hat */}
                  <ellipse cx="200" cy="140" rx="36" ry="24" fill="#FAF9F5" />
                  <path d="M 160 142 C 160 115 240 115 240 142 Z" fill="#F0EEE6" stroke="#7C8A6E" strokeWidth="1.5" />
                  <rect x="175" y="112" width="50" height="6" rx="2" fill="#E8763A" />

                  {/* Head & Safety Glasses */}
                  <ellipse cx="200" cy="158" rx="20" ry="22" fill="#E5E1D5" />
                  <rect x="185" y="148" width="30" height="8" rx="3" fill="#1A1F17" opacity="0.8" />
                  
                  {/* Safety Vest / Coveralls */}
                  <path d="M 150 190 C 150 175 250 175 250 190 L 270 380 L 130 380 Z" fill="#7C8A6E" />
                  {/* High-Vis Vest Straps */}
                  <path d="M 170 190 L 180 340 L 220 340 L 230 190" fill="#E8763A" />
                  <rect x="160" y="240" width="80" height="12" fill="#FAF9F5" opacity="0.9" />

                  {/* Arms & Smart Safety Tablet */}
                  <path d="M 140 220 L 180 290 L 220 290 L 260 220" stroke="#7C8A6E" strokeWidth="18" strokeLinecap="round" />
                  
                  {/* Tablet Screen */}
                  <rect x="165" y="255" width="80" height="60" rx="6" fill="#1A1F17" stroke="#FFFFFF" strokeWidth="2" />
                  {/* Tablet Interface details: Highlighted Spans */}
                  <rect x="173" y="265" width="64" height="4" rx="2" fill="#FAF9F5" opacity="0.9" />
                  <rect x="173" y="274" width="40" height="4" rx="2" fill="#B23A2E" /> {/* SIF Span */}
                  <rect x="173" y="283" width="52" height="4" rx="2" fill="#38BDF8" /> {/* LSR Span */}
                  <rect x="173" y="292" width="46" height="4" rx="2" fill="#F2A05C" /> {/* Barrier Span */}
                  <circle cx="230" cy="298" r="4" fill="#10B981" />
                </svg>

                {/* Duotone Ambient Gradient */}
                <div className="absolute inset-0 bg-[#3E4433]/20 mix-blend-multiply pointer-events-none" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent pointer-events-none" />

                {/* Top-Left Small "Swoosh" Decorative Badge */}
                <div className="absolute top-3.5 left-3.5 z-20 flex items-center justify-center w-9 h-9 rounded-full bg-white/90 backdrop-blur-md text-[#E8763A] shadow-md border border-white/50">
                  <Sparkles className="w-5 h-5 fill-current" />
                </div>
              </div>
            </div>

            {/* Overlapping Bottom-Right White Card: Live Detections */}
            <div className="absolute -bottom-5 -right-3 sm:-bottom-6 sm:-right-5 z-30 bg-white text-[#1A1F17] rounded-2xl p-4 shadow-2xl border border-black/5 max-w-[270px] animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="flex items-center space-x-3">
                {/* 3 Small Overlapping Circular Avatars */}
                <div className="flex -space-x-2 shrink-0">
                  <div className="w-8 h-8 rounded-full border-2 border-white bg-[#3E4433] text-[#F0EEE6] flex items-center justify-center text-[10px] font-bold shadow-sm">
                    PP
                  </div>
                  <div className="w-8 h-8 rounded-full border-2 border-white bg-[#7C8A6E] text-white flex items-center justify-center text-[10px] font-bold shadow-sm">
                    RK
                  </div>
                  <div className="w-8 h-8 rounded-full border-2 border-white bg-[#E8763A] text-white flex items-center justify-center text-[10px] font-bold shadow-sm">
                    AM
                  </div>
                </div>

                <div>
                  <div className="font-sans font-bold text-xs sm:text-sm text-[#1A1F17] leading-tight">
                    Live Detections
                  </div>
                  <div className="flex items-center text-[10px] text-emerald-700 font-medium mt-0.5">
                    <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" />
                    <span>Real-time Active</span>
                  </div>
                </div>
              </div>

              {/* Rating-Style Reviewer Agreement Line */}
              <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center space-x-1 text-[11px] text-[#3E4433]">
                <div className="flex text-amber-500">
                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                </div>
                <span className="font-semibold text-[#1A1F17] ml-1">94%</span>
                <span className="text-slate-500 text-[10px]">agreement (1.5k reports)</span>
              </div>
            </div>

          </div>
        </div>

        {/* ================= RIGHT HALF: Headlines, Description & Outline Buttons ================= */}
        <div className="lg:col-span-6 flex flex-col justify-center space-y-6 lg:pl-4">
          
          {/* Large Serif Headline */}
          <div>
            <h2 className="font-serif font-medium text-3xl sm:text-4xl lg:text-[46px] leading-[1.12] tracking-tight text-white drop-shadow-sm">
              Flag the precursor.<br />
              Explain the why.
            </h2>
          </div>

          {/* Plain-Language Explainability Feature Paragraph */}
          <p className="font-sans text-sm sm:text-base text-[#F0EEE6]/90 leading-relaxed font-light max-w-xl">
            SIF Sentinel AI goes beyond black-box classification by highlighting the exact phrases in safety reports that indicate high-potential hazards, administrative and physical barrier failures, and Life-Saving Rule non-compliances. HSE teams get immediate, auditable evidence behind every AI decision.
          </p>

          {/* Two Circular Icon Buttons as Ghost/Outline on Dark Orange */}
          <div className="flex items-center space-x-3 pt-2">
            <button
              onClick={onExploreExplanation}
              title="Inspect Signal Explanations"
              aria-label="Inspect Explanations"
              className="w-11 h-11 rounded-full border-2 border-white/40 hover:border-white hover:bg-white/10 text-white flex items-center justify-center transition-all duration-200 active:scale-95 shadow-sm group"
            >
              <Asterisk className="w-5 h-5 text-white group-hover:rotate-45 transition-transform duration-200" />
            </button>

            <button
              onClick={onViewLsrDetails}
              title="Jump to Life-Saving Rules"
              aria-label="Life-Saving Rules"
              className="w-11 h-11 rounded-full border-2 border-white/40 hover:border-white hover:bg-white/10 text-white flex items-center justify-center transition-all duration-200 active:scale-95 shadow-sm group"
            >
              <ArrowUpRight className="w-5 h-5 text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform duration-200 stroke-[2.2]" />
            </button>
          </div>

        </div>

      </div>

      {/* ================= BOTTOM-RIGHT SIF SENTINEL LOGOMARK ================= */}
      <div className="absolute bottom-5 right-6 sm:bottom-7 sm:right-8 z-20 flex items-center space-x-1.5 opacity-80 hover:opacity-100 transition-opacity">
        <div className="w-6 h-6 rounded-lg bg-white/20 backdrop-blur-sm border border-white/30 flex items-center justify-center text-white">
          <Flame className="w-3.5 h-3.5" />
        </div>
        <span className="font-serif font-bold text-xs tracking-tight text-white/90">
          SIF Sentinel AI
        </span>
      </div>

    </section>
  );
};
