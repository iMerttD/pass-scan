import React from "react";
import { PortraitInfo } from "@/lib/types";
import { UserCheck, ShieldCheck, Camera, Maximize2 } from "lucide-react";

interface PortraitCardProps {
  portrait?: PortraitInfo | null;
}

export const PortraitCard: React.FC<PortraitCardProps> = ({ portrait }) => {
  if (!portrait || !portrait.url) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 flex flex-col items-center justify-center text-center h-full min-h-[220px]">
        <Camera className="w-8 h-8 text-zinc-600 mb-2" />
        <span className="text-xs text-zinc-400 font-medium">No Primary Portrait Detected</span>
        <span className="text-[11px] text-zinc-500 mt-1">
          Document photo area could not be isolated confidently
        </span>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2">
        <div className="flex items-center gap-2">
          <UserCheck className="w-4 h-4 text-emerald-400" />
          <h4 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">
            Primary Document Portrait
          </h4>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-300 border border-emerald-800/50">
          {(portrait.confidence * 100).toFixed(0)}% Conf
        </span>
      </div>

      <div className="flex items-center gap-4">
        {/* Extracted Photo Frame */}
        <div className="relative group shrink-0 rounded-lg overflow-hidden border-2 border-zinc-700 bg-zinc-950 shadow-md">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={portrait.url}
            alt="Extracted Passport Portrait"
            className="w-28 h-36 object-cover object-center"
          />
          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center pointer-events-none">
            <Maximize2 className="w-4 h-4 text-white" />
          </div>
        </div>

        {/* Metadata Details */}
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
            <ShieldCheck className="w-4 h-4" />
            <span>Authentic Extraction Only</span>
          </div>
          <p className="text-[11px] text-zinc-400 leading-relaxed">
            No generative AI or facial alterations applied. Isolated via spatial prior geometry and Haar/DNN face localization.
          </p>

          {portrait.bbox && (
            <div className="font-mono text-[10px] text-zinc-500 bg-zinc-950/60 px-2 py-1 rounded border border-zinc-800">
              ROI: [{portrait.bbox.join(", ")}]
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
