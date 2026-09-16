import React, { useState, useRef } from "react";
import { UploadCloud, FileText, ArrowUpRight, Check, AlertCircle } from "lucide-react";

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
    if (isLoading || !files || files.length === 0) return;
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
    <div className="intake-layout">
      <section className="intake-document" aria-labelledby="intake-heading">
        <div className="section-heading"><div><span className="section-eyebrow">DOCUMENT INTAKE</span><h2 id="intake-heading">Add a passport</h2></div><span className="format-tag">01 / 03</span></div>
        <p className="section-description">Upload the identity page to begin a new examination.</p>
        <div
          className={`upload-surface ${isDragOver ? "is-dragging" : ""}`}
          onDragOver={(event) => { event.preventDefault(); if (!isLoading) setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={(event) => { event.preventDefault(); setIsDragOver(false); handleFiles(event.dataTransfer.files); }}
        >
          <div className="upload-symbol"><UploadCloud size={30} strokeWidth={1.4} /></div>
          <h3>Drop your document here</h3>
          <p>A clear photo or scan of the full identity page.</p>
          <button className="office-button office-button--primary" type="button" disabled={isLoading} onClick={() => fileInputRef.current?.click()}>
            <FileText size={16} />Select document
          </button>
          <span className="upload-limit">JPG, PNG, WEBP, HEIC or PDF · up to 15 MB</span>
          <input ref={fileInputRef} type="file" disabled={isLoading} aria-label="Select passport document" accept="image/jpeg,image/png,image/webp,image/heic,image/heif,application/pdf,.heic,.heif" className="hidden" onChange={(event) => { handleFiles(event.target.files); event.target.value = ""; }} />
        </div>
        {errorMsg && <div role="alert" className="intake-error"><AlertCircle size={18} /><span>{errorMsg}</span></div>}
        <div className="intake-note"><FileText size={16} /><span>One document per examination. Review extracted information before confirming.</span></div>
        <section className="sample-library" aria-labelledby="samples-heading">
          <div className="sample-library__heading"><h3 id="samples-heading">Sample documents</h3><span>Training records · no personal data</span></div>
          <div className="sample-list">
            {[
              { variant: "clean", name: "Standard passport", detail: "Valid TD3 specimen", tag: "STANDARD" },
              { variant: "skewed", name: "Rotated document", detail: "Automatic alignment check", tag: "ALIGNMENT" },
              { variant: "blurry", name: "Blurred photograph", detail: "Image sharpness check", tag: "QUALITY" },
              { variant: "glare", name: "Flash reflection", detail: "Glare detection check", tag: "QUALITY" },
            ].map((sample) => (
              <button key={sample.variant} type="button" disabled={isLoading} onClick={() => onSampleSelected(sample.variant)} className="sample-row">
                <FileText size={18} /><span className="sample-name">{sample.name}<small>{sample.detail}</small></span><span className="sample-tag">{sample.tag}</span><ArrowUpRight size={16} />
              </button>
            ))}
          </div>
        </section>
      </section>
      <aside className="intake-guide" aria-label="Document preparation guide">
        <span className="section-eyebrow">BEFORE YOU BEGIN</span>
        <h2>Prepare your document</h2>
        <p>A complete, readable image makes the examination more reliable.</p>
        <ol className="preparation-list">
          <li><Check size={16} /><div><strong>Include the full identity page</strong><p>Keep all four edges and both machine-readable lines visible.</p></div></li>
          <li><Check size={16} /><div><strong>Use even lighting</strong><p>Avoid reflections, flash glare and shadows over the text.</p></div></li>
          <li><Check size={16} /><div><strong>Keep text in focus</strong><p>Place the document flat and hold the camera directly above it.</p></div></li>
        </ol>
        <div className="process-summary"><span className="section-eyebrow">WHAT HAPPENS NEXT</span><h3>You remain in control.</h3><p>The document is analyzed, its fields are extracted, and any uncertainty is flagged for your review. A record is finalized only after your confirmation.</p></div>
        <div className="reference-note"><span>DOCUMENT STANDARD</span><strong>ICAO Doc 9303</strong><small>Machine-readable travel documents</small></div>
      </aside>
    </div>
  );
};
