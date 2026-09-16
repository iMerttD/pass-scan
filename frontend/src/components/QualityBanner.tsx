import React from "react";
import { QualityData } from "@/lib/types";
import { CheckCircle2, AlertTriangle, XCircle, Gauge, SunMedium, Scan } from "lucide-react";

interface QualityBannerProps {
  quality: QualityData;
}

export const QualityBanner: React.FC<QualityBannerProps> = ({ quality }) => {
  const hasWarnings = quality.actionable_feedback.length > 0;
  const isSevere = !quality.acceptable;

  return (
    <div
      className={`state-transition w-full rounded-xl border p-4 ${
        isSevere
          ? "bg-rose-950/30 border-rose-900/60 text-rose-200"
          : hasWarnings
          ? "bg-amber-950/20 border-amber-900/50 text-amber-200"
          : "bg-emerald-950/20 border-emerald-900/40 text-emerald-200"
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-zinc-800/60">
        <div className="flex items-center gap-2.5">
          {isSevere ? (
            <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
          ) : hasWarnings ? (
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
          ) : (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          )}

          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider">
              {isSevere
                ? "Quality Gate Warning: Unfavorable Conditions"
                : hasWarnings
                ? "Quality Gate: Usable with Advisory"
                : "Image Quality Passed All Gates"}
            </h4>
            <span className="text-[11px] text-zinc-400">
              Optical verification metrics evaluated before document extraction
            </span>
          </div>
        </div>

        {/* Quality Metric Badges */}
        <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
          {/* Sharpness */}
          <div className="flex items-center gap-1.5 border-l border-zinc-800 px-2.5 py-1 text-zinc-300">
            <Gauge className="w-3.5 h-3.5 text-zinc-400" />
            <span>Sharpness:</span>
            <span className={quality.blur_score > 0.5 ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
              {(quality.blur_score * 100).toFixed(0)}%
            </span>
          </div>

          {/* Glare */}
          <div className="flex items-center gap-1.5 border-l border-zinc-800 px-2.5 py-1 text-zinc-300">
            <SunMedium className="w-3.5 h-3.5 text-zinc-400" />
            <span>Glare:</span>
            <span className={quality.glare_detected ? "text-rose-400 font-bold" : "text-emerald-400 font-bold"}>
              {quality.glare_detected ? `${(quality.glare_ratio * 100).toFixed(1)}%` : "None"}
            </span>
          </div>

          {/* Resolution */}
          <div className="flex items-center gap-1.5 border-l border-zinc-800 px-2.5 py-1 text-zinc-300">
            <Scan className="w-3.5 h-3.5 text-zinc-400" />
            <span>Dimensions:</span>
            <span className="text-zinc-200">
              {quality.dimensions[0]}x{quality.dimensions[1]}
            </span>
          </div>
        </div>
      </div>

      {/* Actionable Feedback List */}
      {hasWarnings && (
        <div className="mt-3 space-y-1">
          {quality.actionable_feedback.map((item, idx) => (
            <div key={idx} className="text-xs flex items-start gap-2 text-zinc-300">
              <span className="text-amber-400">•</span>
              <span>{item}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
