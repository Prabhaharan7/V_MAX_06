import React from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowUpRight,
  Asterisk,
  Shield,
  Flame,
} from "lucide-react";

interface FeatureCardsSectionProps {
  className?: string;
  onExplorePatterns?: () => void;
}

export const FeatureCardsSection: React.FC<FeatureCardsSectionProps> = ({
  className = "",
  onExplorePatterns,
}) => {
  const navigate = useNavigate();

  return (
    <section
      className={`relative w-full rounded-[32px] bg-[#F0EEE6] text-[#1A1F17] p-8 sm:p-10 lg:p-14 border border-[#B9C2A8]/40 shadow-none overflow-hidden select-none ${className}`}
    >
      {/* Subtle organic background accent */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-40 mix-blend-multiply"
        style={{
          backgroundImage: `radial-gradient(#7C8A6E 0.6px, transparent 0.6px)`,
          backgroundSize: "24px 24px"
        }}
      />

      {/* ================= 1. SECTION HEADER ================= */}
      <div className="relative z-10 flex items-start justify-between mb-10 lg:mb-12">
        <div>
          <h2 className="font-serif font-medium text-3xl sm:text-4xl lg:text-5xl tracking-tight text-[#1A1F17] leading-[1.12]">
            Sites, Patterns,<br className="hidden sm:inline" /> and You
          </h2>
          <p className="mt-2.5 text-sm sm:text-base text-[#4D5947] font-sans font-light max-w-xl">
            Streamlined safety reporting, proactive pattern recognition, and telemetry across all Oil India field operations.
          </p>
        </div>

        {/* Small Logomark Icon Aligned Top-Right of Headline */}
        <div className="shrink-0 flex items-center justify-center w-12 h-12 rounded-2xl bg-[#3E4433] text-[#F0EEE6] border border-[#7C8A6E]/40 shadow-none">
          <Flame className="w-6 h-6 text-[#E8763A]" />
        </div>
      </div>

      {/* ================= 2. THREE CARDS IN A ROW ================= */}
      <div className="relative z-10 grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8 items-stretch">
        
        {/* ================= CARD 1: Submit a Report ================= */}
        <div 
          onClick={() => navigate("/submit")}
          className="group relative bg-[#FFFFFF] rounded-[24px] p-7 sm:p-8 flex flex-col justify-between border border-[#B9C2A8]/40 border-t-4 border-t-[#7C8A6E] shadow-none hover:border-[#3E4433]/40 transition-colors duration-200 cursor-pointer min-h-[280px]"
        >
          <div>
            <div className="flex items-center space-x-2 text-xs font-sans text-[#7C8A6E] font-medium mb-3">
              <span className="w-2 h-2 rounded-full bg-[#7C8A6E]" />
              <span>Field Ingestion</span>
            </div>
            <h3 className="font-serif font-semibold text-2xl text-[#1A1F17] tracking-tight group-hover:text-[#3E4433] transition-colors">
              Submit a Report
            </h3>
            <p className="text-sm text-[#4D5947] font-sans font-light mt-2.5 leading-relaxed">
              Log a UA/UC, near-miss, or incident from the field with real-time AI precursor analysis.
            </p>
          </div>

          {/* Bottom-Right Dark Circular Icon Graphic (Two Overlapping Circles + Safety Shield Icon) */}
          <div className="flex justify-end mt-8">
            <div className="relative flex items-center">
              {/* Outer circle graphic overlay */}
              <div className="w-12 h-12 rounded-full bg-[#272E23]/20 -mr-6 group-hover:-translate-x-1 transition-transform duration-200" />
              {/* Primary dark circle with shield icon */}
              <div className="relative z-10 w-13 h-13 w-[50px] h-[50px] rounded-full bg-[#1A1F17] text-white flex items-center justify-center group-hover:scale-105 transition-transform duration-200">
                <Shield className="w-5 h-5 text-[#E8763A]" />
              </div>
            </div>
          </div>
        </div>

        {/* ================= CARD 2: Explore Precursor Patterns ================= */}
        <div 
          onClick={() => {
            if (onExplorePatterns) {
              onExplorePatterns();
            } else {
              navigate("/review-queue");
            }
          }}
          className="group relative bg-[#FFFFFF] rounded-[24px] p-7 sm:p-8 flex flex-col justify-between border border-[#B9C2A8]/40 border-t-4 border-t-[#7C8A6E] shadow-none hover:border-[#3E4433]/40 transition-colors duration-200 cursor-pointer min-h-[280px]"
        >
          <div>
            <div className="flex items-center space-x-2 text-xs font-sans text-[#7C8A6E] font-medium mb-3">
              <span className="w-2 h-2 rounded-full bg-[#7C8A6E]" />
              <span>Pattern Mining</span>
            </div>
            <h3 className="font-serif font-semibold text-2xl text-[#1A1F17] tracking-tight group-hover:text-[#3E4433] transition-colors">
              Explore Precursor Patterns
            </h3>
            <p className="text-sm text-[#4D5947] font-sans font-light mt-2.5 leading-relaxed">
              See recurring activity, location, and barrier-failure combinations across 90-day windows.
            </p>
          </div>

          {/* Bottom-Right Circular Icon Buttons (Asterisk + Diagonal Arrow) */}
          <div className="flex justify-end items-center space-x-2.5 mt-8">
            <button
              type="button"
              title="Inspect Signals"
              aria-label="Inspect Signals"
              className="w-11 h-11 rounded-full bg-[#FAF9F5] border border-[#B9C2A8]/60 text-[#1A1F17] flex items-center justify-center hover:bg-[#3E4433] hover:text-white transition-all duration-200 group-hover:scale-105"
            >
              <Asterisk className="w-5 h-5" />
            </button>
            <button
              type="button"
              title="Explore Patterns"
              aria-label="Explore Patterns"
              className="w-11 h-11 rounded-full bg-[#1A1F17] text-white flex items-center justify-center hover:bg-[#3E4433] transition-all duration-200 group-hover:scale-105"
            >
              <ArrowUpRight className="w-5 h-5 stroke-[2.2]" />
            </button>
          </div>
        </div>

        {/* ================= CARD 3: Find your site's risk profile ================= */}
        <div 
          onClick={() => navigate("/sites")}
          className="group relative bg-[#3E4433] text-white rounded-[24px] p-7 sm:p-8 flex flex-col justify-between border border-[#7C8A6E]/30 shadow-none hover:bg-[#353B2B] transition-colors duration-200 cursor-pointer min-h-[280px]"
        >
          <div>
            <div className="flex items-center space-x-2 text-xs font-sans text-[#B9C2A8] font-medium mb-3">
              <span className="w-2 h-2 rounded-full bg-[#E8763A]" />
              <span>Asset Telemetry</span>
            </div>
            <h3 className="font-serif font-semibold text-2xl text-white tracking-tight">
              Find your site's risk profile
            </h3>
            <p className="text-sm text-[#F0EEE6]/85 font-sans font-light mt-2.5 leading-relaxed">
              Track asset-level Safety Improvement Index (SII) scores, barrier recurrence trends, and 30-day forecast risk telemetry.
            </p>
          </div>

          {/* Bottom-Left Aligned White Pill Button */}
          <div className="flex justify-start mt-8">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                navigate("/sites");
              }}
              className="bg-white text-[#1A1F17] hover:bg-[#FAF9F5] font-sans font-medium text-xs sm:text-sm px-5 py-2.5 rounded-full inline-flex items-center gap-2 transition-transform duration-200 group-hover:scale-105 shadow-none"
            >
              <span>View Sites</span>
              <ArrowUpRight className="w-4 h-4 stroke-[2.2]" />
            </button>
          </div>
        </div>

      </div>
    </section>
  );
};
