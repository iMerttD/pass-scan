import React, { useState, useRef } from "react";
import { UploadCloud, FileText, Image as ImageIcon, Sparkles, AlertCircle, ShieldAlert } from "lucide-react";

const ACCEPTED_MIME_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/heic",
  "image/heif",
  "application/pdf",
];

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
  onSampleSelected: (variant: string) => void;
  isLoading: boolean;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFileSelected,
  onSampleSelected,
  isLoading,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    setErrorMsg(null);

    if (file.size === 0) {
      setErrorMsg("The selected file is empty.");
      return;
    }

    // Validate size (< 15MB)
    if (file.size > 15 * 1024 * 1024) {
      setErrorMsg("File size exceeds 15MB limit.");
      return;
    }

    // Validate type up front so a mistaken drop never round-trips to the server.
    // Some browsers report an empty MIME type for HEIC, so the extension counts too.
    const extensionOk = /\.(jpe?g|png|webp|pdf|heic|heif)$/i.test(file.name);
    if (!ACCEPTED_MIME_TYPES.includes(file.type) && !extensionOk) {
      setErrorMsg("Unsupported file type. Please upload a JPG, PNG, WEBP, HEIC or PDF file.");
      return;
    }

    onFileSelected(file);
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Upload Box */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => !isLoading && fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            if (!isLoading) fileInputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={isLoading ? -1 : 0}
        aria-label="Upload passport identity page. Accepted formats: JPG, PNG, WEBP, HEIC, PDF. Maximum 15 megabytes."
        aria-disabled={isLoading}
        className={`relative focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950 flex flex-col items-center justify-center p-10 rounded-2xl border-2 border-dashed transition-all cursor-pointer ${
          isDragOver
            ? "border-emerald-500 bg-emerald-950/20 scale-[1.01]"
            : "border-zinc-700 hover:border-zinc-500 bg-zinc-900/50 hover:bg-zinc-900/80"
        } ${isLoading ? "opacity-60 pointer-events-none" : ""}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/heic,image/heif,application/pdf,.heic,.heif"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />

        <div className="h-16 w-16 mb-4 rounded-2xl bg-zinc-800/90 border border-zinc-700 flex items-center justify-center text-zinc-300 shadow-inner">
          <UploadCloud className="w-8 h-8 text-emerald-400" />
        </div>

        <h3 className="text-lg font-medium text-zinc-100 mb-1">
          Upload Passport Identity Page
        </h3>
        <p className="text-xs text-zinc-400 max-w-md text-center mb-4 leading-relaxed">
          Drag & drop a high-resolution photo or PDF scan. Image is analyzed entirely on your local CPU/GPU with strict privacy guarantees.
        </p>

        <div className="flex items-center gap-2 text-[11px] font-mono text-zinc-400 bg-zinc-950/80 px-3 py-1.5 rounded-lg border border-zinc-800">
          <span className="text-zinc-500">FORMATS:</span>
          <span className="text-emerald-400 font-semibold">JPG</span>
          <span>•</span>
          <span className="text-emerald-400 font-semibold">PNG</span>
          <span>•</span>
          <span className="text-emerald-400 font-semibold">WEBP</span>
          <span>•</span>
          <span className="text-emerald-400 font-semibold">HEIC</span>
          <span>•</span>
          <span className="text-emerald-400 font-semibold">PDF</span>
          <span>(Max 15MB)</span>
        </div>

        {errorMsg && (
          <div role="alert" className="mt-4 flex items-center gap-2 text-xs text-rose-400 bg-rose-950/40 px-3 py-1.5 rounded-md border border-rose-900">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
      </div>

      {/* Synthetic Demo Specimens */}
      <div className="bg-zinc-900/40 rounded-xl p-4 border border-zinc-800/80">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">
              Synthetic Test Specimens (No Real Personal Data Needed)
            </span>
          </div>
          <span className="text-[11px] text-zinc-400 font-mono">1-Click Test</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <button
            type="button"
            disabled={isLoading}
            onClick={() => onSampleSelected("clean")}
            className="flex flex-col text-left p-2.5 rounded-lg bg-zinc-800/60 hover:bg-zinc-800 border border-zinc-700/60 hover:border-emerald-500/50 transition-all group"
          >
            <span className="text-xs font-medium text-zinc-200 group-hover:text-emerald-400 flex items-center gap-1.5">
              <span>Standard Passport</span>
            </span>
            <span className="text-[10px] text-zinc-400 mt-0.5">Valid TD3 ICAO Specimen</span>
          </button>

          <button
            type="button"
            disabled={isLoading}
            onClick={() => onSampleSelected("skewed")}
            className="flex flex-col text-left p-2.5 rounded-lg bg-zinc-800/60 hover:bg-zinc-800 border border-zinc-700/60 hover:border-emerald-500/50 transition-all group"
          >
            <span className="text-xs font-medium text-zinc-200 group-hover:text-emerald-400 flex items-center gap-1.5">
              <span>Skewed / Rotated</span>
            </span>
            <span className="text-[10px] text-zinc-400 mt-0.5">Tests Auto-Deskew</span>
          </button>

          <button
            type="button"
            disabled={isLoading}
            onClick={() => onSampleSelected("blurry")}
            className="flex flex-col text-left p-2.5 rounded-lg bg-zinc-800/60 hover:bg-zinc-800 border border-zinc-700/60 hover:border-amber-500/50 transition-all group"
          >
            <span className="text-xs font-medium text-zinc-200 group-hover:text-amber-400 flex items-center gap-1.5">
              <span>Blurry Photo</span>
            </span>
            <span className="text-[10px] text-zinc-400 mt-0.5">Tests Blur Quality Gate</span>
          </button>

          <button
            type="button"
            disabled={isLoading}
            onClick={() => onSampleSelected("glare")}
            className="flex flex-col text-left p-2.5 rounded-lg bg-zinc-800/60 hover:bg-zinc-800 border border-zinc-700/60 hover:border-rose-500/50 transition-all group"
          >
            <span className="text-xs font-medium text-zinc-200 group-hover:text-rose-400 flex items-center gap-1.5">
              <span>Flash Glare</span>
            </span>
            <span className="text-[10px] text-zinc-400 mt-0.5">Tests Specular Glare Gate</span>
          </button>
        </div>
      </div>
    </div>
  );
};
