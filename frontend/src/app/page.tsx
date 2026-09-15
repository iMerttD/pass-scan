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
  Lock,
  ArrowRight,
  RotateCcw,
  Sparkles,
} from "lucide-react";

export default function PassportApp() {
  const [analysis, setAnalysis] = useState<PassportAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [isSubmittingConfirm, setIsSubmittingConfirm] = useState(false);
  const [confirmedSuccess, setConfirmedSuccess] = useState(false);
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
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-zinc-950">
      <Header onReset={handleReset} hasActiveSession={!!analysis} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Backend Connectivity Status Bar */}
        {backendStatus && backendStatus.status === "offline" && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>
              Backend server is not running on <strong>http://127.0.0.1:8000</strong>. Please start the FastAPI backend service.
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
          <div className="py-8">
            <UploadZone
              onFileSelected={handleFileUpload}
              onSampleSelected={handleSampleSelect}
              isLoading={isLoading}
            />
          </div>
        )}

        {/* Results & Human Review Console */}
        {analysis && !isLoading && (
          <div className="space-y-6 animate-in fade-in duration-200">
            {/* Top Quality Gate Status Banner */}
            <QualityBanner quality={analysis.quality} />

            {/* Main Review Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Visual Evidences (Portrait, Document Canvas, MRZ) */}
              <div className="lg:col-span-6 space-y-6">
                {/* Portrait Crop */}
                <PortraitCard portrait={analysis.portrait} />

                {/* Original Document Viewer */}
                <DocumentViewer
                  normalizedImageUrl={analysis.normalized_image_url}
                  annotatedImageUrl={analysis.annotated_image_url}
                />

                {/* ICAO Doc 9303 MRZ Engine Breakdown */}
                <MRZInspector mrz={analysis.mrz} />
              </div>

              {/* Right Column: Extracted Fields Review & Inline Editing */}
              <div className="lg:col-span-6 flex flex-col justify-between space-y-6 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 shadow-lg">
                <div className="space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
                    <div>
                      <h3 className="text-sm font-semibold text-zinc-100">
                        Identity Fields Review
                      </h3>
                      <p className="text-xs text-zinc-400">
                        Review, edit, or adjust uncertain fields before final confirmation
                      </p>
                    </div>

                    {/* Overall Confidence Pill */}
                    <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-zinc-950 border border-zinc-700 font-mono text-xs">
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
                <div className="pt-4 border-t border-zinc-800/80 flex flex-col sm:flex-row items-center justify-between gap-3">
                  <button
                    onClick={handleReset}
                    className="w-full sm:w-auto flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium transition-colors"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Discard & Reset</span>
                  </button>

                  <button
                    onClick={() => setIsConfirmModalOpen(true)}
                    className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 text-xs font-bold shadow-lg shadow-emerald-500/20 transition-all cursor-pointer"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>Confirm & Finalize Document</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

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
