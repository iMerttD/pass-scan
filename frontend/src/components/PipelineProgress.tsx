import React from "react";
import { Loader2 } from "lucide-react";

interface PipelineProgressProps {
  currentStage?: string;
}

const STAGES = [
  "File Validation & Magic Bytes",
  "Perspective Correction & Deskew",
  "Image Quality Gate Assessment",
  "Primary Portrait Extraction",
  "MRZ Detection & ICAO 9303 Parsing",
  "Multilingual Visual OCR",
  "Cross-Validation & Reconciliation",
];

export const PipelineProgress: React.FC<PipelineProgressProps> = () => {
  return (
    <div className="w-full max-w-xl mx-auto my-12 p-8 rounded-2xl bg-zinc-900/80 border border-zinc-800 shadow-2xl backdrop-blur-sm text-center">
      <div className="inline-flex p-3.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 mb-4 animate-pulse">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>

      <h3 className="text-base font-semibold text-zinc-100 mb-1">
        Document examination in progress
      </h3>
      <p className="text-xs text-zinc-400 mb-6">
        Validating and extracting the document on this workstation
      </p>

      <div className="space-y-2 text-left">
        {STAGES.map((stage, idx) => (
          <div
            key={idx}
            className="flex items-center gap-3 px-3.5 py-2 rounded-lg bg-zinc-950/60 border border-zinc-800/80 text-xs font-mono text-zinc-300"
          >
            <div className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="text-zinc-500 font-semibold">{idx + 1}.</span>
            <span className="text-zinc-300">{stage}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
