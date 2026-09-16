import React from "react";
import { MRZData } from "@/lib/types";
import { CheckCircle2, XCircle, FileCode } from "lucide-react";

interface MRZInspectorProps {
  mrz: MRZData;
}

export const MRZInspector: React.FC<MRZInspectorProps> = ({ mrz }) => {
  const { checks } = mrz;

  const renderCheckItem = (label: string, isValid?: boolean | null) => {
    return (
      <div className="flex items-center justify-between p-2 rounded bg-zinc-950/70 border border-zinc-800/80 text-xs font-mono">
        <span className="text-zinc-300">{label}</span>
        {isValid === true ? (
          <span className="flex items-center gap-1 text-emerald-400 font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>PASS</span>
          </span>
        ) : isValid === false ? (
          <span className="flex items-center gap-1 text-rose-400 font-semibold">
            <XCircle className="w-3.5 h-3.5" />
            <span>FAIL</span>
          </span>
        ) : (
          <span className="text-zinc-500">N/A</span>
        )}
      </div>
    );
  };

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 space-y-4">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-emerald-400" />
          <h4 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">
            ICAO Doc 9303 MRZ Engine Breakdown
          </h4>
        </div>
        <span
          className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
            mrz.valid
              ? "bg-emerald-950/60 text-emerald-300 border-emerald-800/60"
              : "bg-rose-950/60 text-rose-300 border-rose-800/60"
          }`}
        >
          {mrz.valid ? "ALL CHECKSUMS PASSED" : "CHECKSUM FAILED"}
        </span>
      </div>

      {/* Raw MRZ Character Lines */}
      <div>
        <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block mb-1.5">
          Raw TD3 Lines (44 characters per line)
        </span>
        <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 overflow-x-auto">
          {mrz.raw_lines.length > 0 ? (
            <div className="space-y-1 font-mono text-xs sm:text-sm tracking-[0.18em] text-emerald-400 select-all font-bold">
              {mrz.raw_lines.map((line, idx) => (
                <div key={idx} className="whitespace-pre">
                  {line}
                </div>
              ))}
            </div>
          ) : (
            <span className="text-xs font-mono text-zinc-500 italic">
              No MRZ lines localized
            </span>
          )}
        </div>
      </div>

      {/* Checksum Breakdown Matrix */}
      <div>
        <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block mb-1.5">
          ICAO 7-3-1 Modulo 10 Check Digits
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {renderCheckItem("Document Number Check Digit", checks.document_number_checksum)}
          {renderCheckItem("Date of Birth Check Digit", checks.birth_date_checksum)}
          {renderCheckItem("Expiry Date Check Digit", checks.expiry_date_checksum)}
          {renderCheckItem("Composite Integrity Checksum", checks.composite_checksum)}
        </div>
      </div>

      {/* Error Corrections Applied */}
      {mrz.error_corrections_applied && mrz.error_corrections_applied.length > 0 && (
        <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800 text-[11px] font-mono text-zinc-400">
          <span className="text-amber-400 font-semibold block mb-1">
            Checksum-Guided Corrections Applied:
          </span>
          <ul className="list-disc list-inside space-y-0.5">
            {mrz.error_corrections_applied.map((corr, idx) => (
              <li key={idx}>{corr}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
