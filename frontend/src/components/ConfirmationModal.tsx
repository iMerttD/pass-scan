import React, { useState } from "react";
import { DocumentInfo, HolderInfo, PassportData } from "@/lib/types";
import { CheckCircle, ShieldCheck, Download, Copy, X } from "lucide-react";

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (notes?: string) => Promise<void>;
  document: DocumentInfo;
  holder: HolderInfo;
  passport: PassportData;
  isSubmitting: boolean;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  document,
  holder,
  passport,
  isSubmitting,
}) => {
  const [confirmedCheckbox, setConfirmedCheckbox] = useState(false);
  const [notes, setNotes] = useState("");
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const exportPayload = {
    document,
    holder,
    passport,
    confirmed_at: new Date().toISOString(),
    audit_notes: notes || null,
  };

  const jsonString = JSON.stringify(exportPayload, null, 2);

  const handleCopyJson = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadJson = () => {
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = window.document.createElement("a");
    a.href = url;
    a.download = `passport_${passport.passport_number || "verified"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };


  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirmation-title"
        className="w-full max-w-2xl rounded-2xl bg-zinc-900 border border-zinc-700 shadow-2xl p-6 space-y-5 text-zinc-100"
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 id="confirmation-title" className="text-sm font-semibold text-zinc-100">
                Final Verification & Confirmation
              </h3>
              <p className="text-xs text-zinc-400">
                Confirm audited identity data before storing or exporting
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close confirmation dialog"
            className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Verification Summary */}
        <div className="rounded-lg bg-zinc-950 p-4 border border-zinc-800 grid grid-cols-2 gap-3 text-xs font-mono">
          <div>
            <span className="text-zinc-500 text-[10px] block">PASSPORT NUMBER</span>
            <span className="text-zinc-100 font-bold">{passport.passport_number || "N/A"}</span>
          </div>
          <div>
            <span className="text-zinc-500 text-[10px] block">FULL NAME</span>
            <span className="text-zinc-100 font-bold">
              {holder.given_names} {holder.surname}
            </span>
          </div>
          <div>
            <span className="text-zinc-500 text-[10px] block">NATIONALITY</span>
            <span className="text-zinc-100">{holder.nationality || "N/A"}</span>
          </div>
          <div>
            <span className="text-zinc-500 text-[10px] block">DATE OF BIRTH</span>
            <span className="text-zinc-100">{holder.date_of_birth || "N/A"}</span>
          </div>
          <div>
            <span className="text-zinc-500 text-[10px] block">EXPIRY DATE</span>
            <span className="text-zinc-100">{passport.expiry_date || "N/A"}</span>
          </div>
          <div>
            <span className="text-zinc-500 text-[10px] block">ISSUING STATE</span>
            <span className="text-zinc-100">{document.issuing_country || "N/A"}</span>
          </div>
        </div>

        {/* Notes Input */}
        <div>
          <label className="text-xs font-medium text-zinc-300 block mb-1.5">
            Audit / Reviewer Notes (Optional)
          </label>
          <input
            type="text"
            placeholder="e.g. Identity verified by operator against physical passport."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            aria-describedby="reviewer-notes-helper"
            className="w-full px-3 py-2 text-xs rounded bg-zinc-950 border border-zinc-700 text-zinc-200 focus:outline-none focus:border-emerald-500"
          />
          <p id="reviewer-notes-helper" className="field-helper mt-1 text-[10px] text-zinc-500">
            Optional note stored with the local verification record.
          </p>
        </div>

        {/* Checkbox */}
        <label className="flex items-start gap-2.5 p-3 rounded-lg bg-zinc-950/60 border border-zinc-800 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={confirmedCheckbox}
            onChange={(e) => setConfirmedCheckbox(e.target.checked)}
            className="mt-0.5 rounded border-zinc-700 text-emerald-500 focus:ring-emerald-500"
          />
          <span className="text-xs text-zinc-300">
            I hereby confirm that the passport details and holder portrait have been reviewed and match the submitted travel document.
          </span>
        </label>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyJson}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 transition-colors"
            >
              <Copy className="w-3.5 h-3.5" />
              <span>{copied ? "Copied JSON" : "Copy JSON"}</span>
            </button>
            <button
              onClick={handleDownloadJson}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export JSON</span>
            </button>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors"
            >
              Cancel
            </button>
            <button
              disabled={!confirmedCheckbox || isSubmitting}
              onClick={() => onConfirm(notes)}
              className={`state-transition flex items-center justify-center gap-2 px-5 py-2 rounded text-xs font-semibold ${
                confirmedCheckbox && !isSubmitting
                  ? "bg-emerald-500 hover:bg-emerald-400 text-zinc-950 shadow-lg shadow-emerald-500/20 cursor-pointer"
                  : "bg-zinc-800 text-zinc-500 cursor-not-allowed border border-zinc-700"
              }`}
            >
              <CheckCircle className="w-4 h-4" />
              <span>{isSubmitting ? "Saving..." : "Confirm & Finalize"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
