"use client";

import React, { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { UploadZone } from "@/components/UploadZone";
import { PipelineProgress } from "@/components/PipelineProgress";
import { QualityBanner } from "@/components/QualityBanner";
import { PortraitCard } from "@/components/PortraitCard";
import { DocumentViewer } from "@/components/DocumentViewer";
import { FieldReviewTable } from "@/components/FieldReviewTable";
import { MRZInspector } from "@/components/MRZInspector";
import { ConfirmationModal } from "@/components/ConfirmationModal";
import {
  PassportAnalysisResponse,
  DocumentInfo,
  HolderInfo,
  PassportData,
} from "@/lib/types";
import {
  analyzePassportFile,
  loadSamplePassport,
  confirmPassport,
  checkBackendHealth,
} from "@/lib/api";
import {
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  RotateCcw,
  FileInput,
  ScanLine,
  ClipboardCheck,
  ChevronRight,
  Circle,
} from "lucide-react";

export default function PassportApp() {
  const [analysis, setAnalysis] = useState<PassportAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [isSubmittingConfirm, setIsSubmittingConfirm] = useState(false);
  const [confirmedSuccess, setConfirmedSuccess] = useState(false);
  const [reviewTab, setReviewTab] = useState<"identity" | "evidence">("identity");
  const [backendStatus, setBackendStatus] = useState<{
    status: string;
    engine: string;
    offline: boolean;
  } | null>(null);

  // Editable local state copies
  const [docState, setDocState] = useState<DocumentInfo>({
    type: "passport",
    document_type_code: "P",
  });
  const [holderState, setHolderState] = useState<HolderInfo>({});
  const [passportState, setPassportState] = useState<PassportData>({});

  useEffect(() => {
    checkBackendHealth().then(setBackendStatus);
  }, []);

  // Sync state when new analysis arrives
  useEffect(() => {
    if (analysis) {
      setDocState({ ...analysis.document });
      setHolderState({ ...analysis.holder });
      setPassportState({ ...analysis.passport });
      setConfirmedSuccess(false);
      setReviewTab("identity");
    }
  }, [analysis]);

  const handleFileUpload = async (file: File) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await analyzePassportFile(file);
      setAnalysis(data);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to process passport image.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSampleSelect = async (variant: string) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await loadSamplePassport(variant);
      setAnalysis(data);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load sample passport.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFieldChange = (
    section: "document" | "holder" | "passport",
    field: string,
    value: string
  ) => {
    if (section === "document") {
      setDocState((prev) => ({ ...prev, [field]: value }));
    } else if (section === "holder") {
      setHolderState((prev) => ({ ...prev, [field]: value }));
    } else {
      setPassportState((prev) => ({ ...prev, [field]: value }));
    }
  };

  const handleConfirmSave = async (notes?: string) => {
    if (!analysis) return;
    setIsSubmittingConfirm(true);
    try {
      await confirmPassport(analysis.session_id, {
        document: docState,
        holder: holderState,
        passport: passportState,
        confirmed_by_user: true,
        user_notes: notes,
      });
      setConfirmedSuccess(true);
      setIsConfirmModalOpen(false);
    } catch (err: any) {
      setIsConfirmModalOpen(false);
      setErrorMsg(err.message || "Failed to confirm passport record.");
    } finally {
      setIsSubmittingConfirm(false);
    }
  };

  const handleReset = () => {
    setAnalysis(null);
    setErrorMsg(null);
    setConfirmedSuccess(false);
  };

  return (
    <div className="institutional-app office-workspace">
      <Header onReset={handleReset} hasActiveSession={!!analysis && !isLoading} />
      <div className="workspace-layout">
        <aside className="workflow-sidebar" aria-label="Examination progress">
          <div className="sidebar-label">WORKSPACE</div>
          <div className="sidebar-current"><ScanLine size={18} /><span>Passport examination</span></div>
          <div className="sidebar-label sidebar-label--steps">EXAMINATION WORKFLOW</div>
          <ol className="workflow-steps">
            {[
              { title: "Document intake", detail: "Upload an identity page", icon: FileInput },
              { title: "Review & verify", detail: "Inspect extracted information", icon: ScanLine },
              { title: "Confirmation", detail: "Finalize the document record", icon: ClipboardCheck },
            ].map((step, index) => {
              const currentStep = confirmedSuccess ? 2 : analysis || isLoading ? 1 : 0;
              const complete = index < currentStep || confirmedSuccess;
              return <li key={step.title} className={index === currentStep ? "is-current" : complete ? "is-complete" : ""} aria-current={index === currentStep ? "step" : undefined}>
                <span className="step-marker">{complete ? <CheckCircle2 size={17} /> : <step.icon size={17} />}</span>
                <div><strong>{step.title}</strong><small>{step.detail}</small></div>
              </li>;
            })}
          </ol>
          <div className="sidebar-bottom">
            <div className="service-status"><Circle size={8} fill="currentColor" /><span>{!backendStatus ? "Checking service…" : backendStatus.status === "offline" ? "Service unavailable" : "Service connected"}</span></div>
            <p>Operator review console</p>
            <span>ICAO Doc 9303</span>
          </div>
        </aside>
      <div className="workspace-content">
      <main id="main-content" className="workspace-main" tabIndex={-1}>
        <div className="workspace-breadcrumb"><span>Workspace</span><ChevronRight size={12} /><span>Passport examination</span></div>
        <div className="workspace-title">
          <div><h1>{confirmedSuccess ? "Examination completed" : isLoading ? "Analyzing document" : analysis ? "Review examination" : "New examination"}</h1>
          <p>{analysis ? "Compare the document with the extracted information before confirming." : "Submit a passport identity page for extraction and verification."}</p></div>
          <span className="examination-status">{confirmedSuccess ? "Completed" : isLoading ? "Processing" : analysis ? "Awaiting review" : "Ready for intake"}</span>
        </div>
        {/* Backend Connectivity Status Bar */}
        {backendStatus && backendStatus.status === "offline" && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>
              The document service is unavailable. Start the local backend service to process documents.
            </span>
          </div>
        )}

        {/* Global Error Message */}
        {errorMsg && (
          <div role="alert" className="flex items-center gap-2.5 p-4 rounded-xl bg-rose-950/50 border border-rose-800 text-rose-200 text-xs">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
            <div className="flex-1">
              <span className="font-semibold block">Processing Error</span>
              <span>{errorMsg}</span>
            </div>
            <button
              onClick={() => setErrorMsg(null)}
              className="text-xs underline text-rose-300 hover:text-rose-100"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Confirmation Success Toast */}
        {confirmedSuccess && (
          <div className="flex items-center justify-between p-4 rounded-xl bg-emerald-950/40 border border-emerald-800 text-emerald-200 text-xs animate-in fade-in">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <div>
                <span className="font-semibold block">
                  Passport Successfully Audited & Confirmed
                </span>
                <span className="text-emerald-300/80">
                  Verification record has been finalized locally.
                </span>
              </div>
            </div>
            <button
              onClick={handleReset}
              className="px-3 py-1.5 rounded-lg bg-emerald-900/60 hover:bg-emerald-800 text-emerald-100 text-xs font-medium transition-colors"
            >
              Scan Next Document
            </button>
          </div>
        )}

        {/* Loading State */}
        {isLoading && <PipelineProgress />}

        {/* Initial Upload State */}
        {!analysis && !isLoading && (
          <div>
            <UploadZone
              onFileSelected={handleFileUpload}
              onSampleSelected={handleSampleSelect}
              isLoading={isLoading}
            />
          </div>
        )}

        {/* Results & Human Review Console */}
        {analysis && !isLoading && (
          <div className="space-y-6">
            <div className="case-summary"><div><span>DOCUMENT</span><strong>{passportState.passport_number || "Passport"}</strong></div><div><span>DOCUMENT HOLDER</span><strong>{[holderState.given_names, holderState.surname].filter(Boolean).join(" ") || "Not identified"}</strong></div><div><span>EXTRACTION CONFIDENCE</span><strong>{(analysis.confidence.overall * 100).toFixed(1)}%</strong></div></div>
            {/* Top Quality Gate Status Banner */}
            <QualityBanner quality={analysis.quality} />
            <div className="review-navigation" aria-label="Review sections">
              <button type="button" aria-pressed={reviewTab === "identity"} onClick={() => setReviewTab("identity")}>Identity review</button>
              <button type="button" aria-pressed={reviewTab === "evidence"} onClick={() => setReviewTab("evidence")}>Technical evidence</button>
            </div>
            <div hidden={reviewTab !== "evidence"} className="evidence-layout"><MRZInspector mrz={analysis.mrz} /><PortraitCard portrait={analysis.portrait} /></div>

            {/* Main Review Grid */}
            <div hidden={reviewTab !== "identity"} className="review-layout">
              {/* Left Column: Visual Evidences (Portrait, Document Canvas, MRZ) */}
              <div className="review-document">
                <div className="review-document__sticky">
                {/* Portrait Crop */}
                <div className="review-pane-heading"><span className="section-eyebrow">SOURCE DOCUMENT</span><h2>Visual inspection</h2><p>Compare the source with the extracted fields.</p></div>

                {/* Original Document Viewer */}
                <DocumentViewer
                  normalizedImageUrl={analysis.normalized_image_url}
                  annotatedImageUrl={analysis.annotated_image_url}
                />
                </div>

                {/* ICAO Doc 9303 MRZ Engine Breakdown */}
              </div>

              {/* Right Column: Extracted Fields Review & Inline Editing */}
              <div className="review-fields">
                <div className="space-y-4">
                  <div className="review-pane-heading">
                    <div>
                      <span className="section-eyebrow">EXTRACTED INFORMATION</span>
                      <h2>Identity details</h2>
                      <p className="text-xs text-zinc-400">
                        Review, edit, or adjust uncertain fields before final confirmation
                      </p>
                    </div>

                    {/* Overall Confidence Pill */}
                    <div className="hidden">
                      <span className="text-zinc-400">Overall:</span>
                      <span
                        className={
                          analysis.confidence.overall >= 0.85
                            ? "text-emerald-400 font-bold"
                            : analysis.confidence.overall >= 0.65
                            ? "text-amber-400 font-bold"
                            : "text-rose-400 font-bold"
                        }
                      >
                        {(analysis.confidence.overall * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* Field Table with Inline Editing */}
                  <FieldReviewTable
                    document={docState}
                    holder={holderState}
                    passport={passportState}
                    evidence={analysis.confidence.fields}
                    onFieldChange={handleFieldChange}
                  />
                </div>

                {/* Bottom Action Footer */}
              </div>
            </div>
                <div className="review-actions">
                  <span>{confirmedSuccess ? "The record has been finalized." : "Verify all fields before finalizing this record."}</span>
                  <div className="review-actions__buttons">
                  <button
                    onClick={handleReset}
                    className="office-button office-button--secondary"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Discard</span>
                  </button>

                  <button
                    onClick={() => setIsConfirmModalOpen(true)}
                    disabled={confirmedSuccess}
                    className="office-button office-button--primary"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>{confirmedSuccess ? "Confirmed" : "Confirm record"}</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
                </div>
          </div>
        )}
      </main>

      <footer className="workspace-footer"><span>PassportOffice / Document examination</span><span>Operator confirmation required</span></footer>
      </div>
      </div>

      {/* Confirmation & Export Modal */}
      {analysis && (
        <ConfirmationModal
          isOpen={isConfirmModalOpen}
          onClose={() => setIsConfirmModalOpen(false)}
          onConfirm={handleConfirmSave}
          document={docState}
          holder={holderState}
          passport={passportState}
          isSubmitting={isSubmittingConfirm}
        />
      )}
    </div>
  );
}
