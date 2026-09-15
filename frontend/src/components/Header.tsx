import React from "react";
import { ShieldCheck, Lock, Cpu, RotateCcw } from "lucide-react";

interface HeaderProps {
  onReset?: () => void;
  hasActiveSession?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onReset, hasActiveSession }) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-sm shadow-emerald-950">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold text-zinc-100 tracking-tight">
                PASSPORT<span className="text-emerald-400">.LOCAL</span>
              </h1>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                v1.0.0
              </span>
            </div>
            <p className="text-xs text-zinc-400">
              On-Premise ICAO Doc 9303 Identity Extraction & Validation Engine
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Security & Privacy Badges */}
          <div className="hidden md:flex items-center gap-2 text-xs font-mono">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/40 border border-emerald-800/50 text-emerald-300">
              <Lock className="w-3.5 h-3.5 text-emerald-400" />
              <span>100% On-Premise (No Cloud Calls)</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-400">
              <Cpu className="w-3.5 h-3.5 text-zinc-300" />
              <span>Local PP-OCR Engine</span>
            </div>
          </div>

          {hasActiveSession && onReset && (
            <button
              onClick={onReset}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 transition-colors border border-zinc-700"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Analyze Another</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
