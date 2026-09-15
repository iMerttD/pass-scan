import React, { useState } from "react";
import { FieldEvidence, DocumentInfo, HolderInfo, PassportData } from "@/lib/types";
import { CheckCircle, AlertTriangle, AlertCircle, Edit3, ChevronDown, ChevronUp, ShieldCheck } from "lucide-react";

interface FieldReviewTableProps {
  document: DocumentInfo;
  holder: HolderInfo;
  passport: PassportData;
  evidence: Record<string, FieldEvidence>;
  onFieldChange: (section: "document" | "holder" | "passport", field: string, value: string) => void;
}

export const FieldReviewTable: React.FC<FieldReviewTableProps> = ({
  document,
  holder,
  passport,
  evidence,
  onFieldChange,
}) => {
  const [expandedField, setExpandedField] = useState<string | null>(null);

  const toggleExpand = (fieldKey: string) => {
    setExpandedField(expandedField === fieldKey ? null : fieldKey);
  };

  const renderStatusBadge = (ev?: FieldEvidence) => {
    if (!ev) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-zinc-400 border border-zinc-700">
          N/A
        </span>
      );
    }

    if (ev.status === "VERIFIED") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950/60 text-emerald-300 border border-emerald-800/60">
          <CheckCircle className="w-3 h-3 text-emerald-400" />
          <span>Verified</span>
        </span>
      );
    }

    if (ev.status === "VERIFIED WITH WARNING") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-amber-950/60 text-amber-300 border border-amber-800/60">
          <AlertTriangle className="w-3 h-3 text-amber-400" />
          <span>Warning</span>
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950/60 text-rose-300 border border-rose-800/60">
        <AlertCircle className="w-3 h-3 text-rose-400" />
        <span>Needs Review</span>
      </span>
    );
  };

  const renderFieldRow = (
    label: string,
    fieldKey: string,
    value: string | null | undefined,
    section: "document" | "holder" | "passport"
  ) => {
    const ev = evidence[fieldKey];
    const isExpanded = expandedField === fieldKey;
    const isReviewReq = ev?.review_required || !value;

    return (
      <div
        key={fieldKey}
        className={`rounded-lg border transition-all ${
          isReviewReq
            ? "border-rose-900/50 bg-rose-950/10"
            : "border-zinc-800/80 bg-zinc-900/40 hover:bg-zinc-900/70"
        }`}
      >
        <div className="p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Label & Badges */}
          <div className="w-full sm:w-1/3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-zinc-300 tracking-wide">
                {label}
              </span>
              {renderStatusBadge(ev)}
            </div>
            {ev && (
              <span className="text-[10px] font-mono text-zinc-500 mt-0.5 block">
                Confidence: {(ev.confidence * 100).toFixed(1)}% • Source: {ev.source.toUpperCase()}
              </span>
            )}
          </div>

          {/* Editable Value Input */}
          <div className="flex-1 flex items-center gap-2">
            <div className="relative w-full">
              <input
                type="text"
                value={value || ""}
                placeholder={isReviewReq ? "Field not detected — enter manually" : ""}
                onChange={(e) => onFieldChange(section, fieldKey, e.target.value)}
                className={`w-full px-3 py-1.5 text-xs font-mono rounded bg-zinc-950/90 border text-zinc-100 focus:outline-none transition-colors ${
                  isReviewReq
                    ? "border-rose-700/80 focus:border-rose-500 placeholder-rose-400/50"
                    : "border-zinc-700 focus:border-emerald-500"
                }`}
              />
              <Edit3 className="w-3.5 h-3.5 text-zinc-500 absolute right-2.5 top-2 pointer-events-none" />
            </div>

            {/* Evidence Drawer Toggle */}
            {ev && (
              <button
                type="button"
                onClick={() => toggleExpand(fieldKey)}
                className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                title="Inspect OCR vs MRZ Evidence"
              >
                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            )}
          </div>
        </div>

        {/* Expanded Evidence Drawer */}
        {isExpanded && ev && (
          <div className="px-3.5 py-2.5 bg-zinc-950/90 border-t border-zinc-800/80 text-[11px] font-mono grid grid-cols-2 sm:grid-cols-4 gap-2 text-zinc-400">
            <div>
              <span className="text-zinc-600 block text-[10px]">MRZ VALUE</span>
              <span className="text-zinc-200">{ev.mrz_value || "<none>"}</span>
            </div>
            <div>
              <span className="text-zinc-600 block text-[10px]">VISUAL OCR</span>
              <span className="text-zinc-200">{ev.visual_value || "<none>"}</span>
            </div>
            <div>
              <span className="text-zinc-600 block text-[10px]">CHECKSUM</span>
              <span className={ev.checksum_valid === true ? "text-emerald-400" : ev.checksum_valid === false ? "text-rose-400" : "text-zinc-500"}>
                {ev.checksum_valid === true ? "PASS" : ev.checksum_valid === false ? "FAIL" : "N/A"}
              </span>
            </div>
            <div>
              <span className="text-zinc-600 block text-[10px]">SOURCES MATCH</span>
              <span className={ev.sources_match ? "text-emerald-400" : "text-amber-400"}>
                {ev.sources_match ? "AGREE" : "DISCREPANCY"}
              </span>
            </div>
            {ev.note && (
              <div className="col-span-2 sm:col-span-4 mt-1 text-[10px] text-zinc-400 italic">
                Note: {ev.note}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* 1. Document Data */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5 pb-1 border-b border-zinc-800">
          <span>Document & Passport Information</span>
        </h4>
        <div className="space-y-2">
          {renderFieldRow("Passport Number", "passport_number", passport.passport_number, "passport")}
          {renderFieldRow("Issuing Country", "issuing_country", document.issuing_country, "document")}
          {renderFieldRow("Document Type", "document_type_code", document.document_type_code, "document")}
        </div>
      </div>

      {/* 2. Holder Data */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5 pb-1 border-b border-zinc-800">
          <span>Holder Identity & Demographics</span>
        </h4>
        <div className="space-y-2">
          {renderFieldRow("Surname / Nom", "surname", holder.surname, "holder")}
          {renderFieldRow("Given Names / Prénoms", "given_names", holder.given_names, "holder")}
          {renderFieldRow("Nationality", "nationality", holder.nationality, "holder")}
          {renderFieldRow("Date of Birth (YYYY-MM-DD)", "date_of_birth", holder.date_of_birth, "holder")}
          {renderFieldRow("Sex", "sex", holder.sex, "holder")}
          {renderFieldRow("Place of Birth", "place_of_birth", holder.place_of_birth, "holder")}
        </div>
      </div>

      {/* 3. Validity & Authority */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5 pb-1 border-b border-zinc-800">
          <span>Validity & Issuing Authority</span>
        </h4>
        <div className="space-y-2">
          {renderFieldRow("Date of Issue", "date_of_issue", passport.issue_date, "passport")}
          {renderFieldRow("Date of Expiry", "expiry_date", passport.expiry_date, "passport")}
          {renderFieldRow("Issuing Authority", "issuing_authority", passport.issuing_authority, "passport")}
        </div>
      </div>
    </div>
  );
};
