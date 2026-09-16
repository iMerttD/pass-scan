import React, { useState } from "react";
import { ZoomIn, ZoomOut, RotateCcw, Layers, Eye } from "lucide-react";

interface DocumentViewerProps {
  normalizedImageUrl?: string | null;
  annotatedImageUrl?: string | null;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  normalizedImageUrl,
  annotatedImageUrl,
}) => {
  const [showAnnotations, setShowAnnotations] = useState(true);
  const [zoom, setZoom] = useState(1);

  const activeImage = showAnnotations && annotatedImageUrl ? annotatedImageUrl : normalizedImageUrl;

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.25, 2.5));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.25, 0.75));
  const handleResetZoom = () => setZoom(1);

  if (!activeImage) {
    return (
      <div className="w-full h-80 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-500 text-xs">
        No document preview available
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 overflow-hidden flex flex-col">
      {/* Control Toolbar */}
      <div className="flex flex-col items-start justify-between gap-3 px-4 py-2.5 bg-zinc-950/80 border-b border-zinc-800 text-xs sm:flex-row sm:items-center">
        <div className="flex w-full flex-wrap items-center justify-between gap-2 sm:w-auto sm:justify-start">
          <Eye className="w-4 h-4 text-zinc-400" />
          <span className="font-semibold text-zinc-200">Document Canvas</span>
          <span className="text-[10px] font-mono text-zinc-500 px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800">
            {Math.round(zoom * 100)}%
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Annotation overlay toggle */}
          {annotatedImageUrl && (
            <button
              onClick={() => setShowAnnotations(!showAnnotations)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors border ${
                showAnnotations
                  ? "bg-emerald-950/50 border-emerald-800/60 text-emerald-300"
                  : "bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>{showAnnotations ? "Overlays ON" : "Clean View"}</span>
            </button>
          )}

          {/* Zoom Controls */}
          <div className="flex items-center bg-zinc-800 rounded border border-zinc-700 p-0.5">
            <button
              onClick={handleZoomOut}
              className="p-1 hover:bg-zinc-700 text-zinc-300 rounded transition-colors"
              title="Zoom out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleResetZoom}
              className="p-1 hover:bg-zinc-700 text-zinc-300 rounded transition-colors"
              title="Reset zoom"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleZoomIn}
              className="p-1 hover:bg-zinc-700 text-zinc-300 rounded transition-colors"
              title="Zoom in"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Image Viewport */}
      <div className="relative w-full h-[460px] overflow-auto bg-zinc-950 flex items-center justify-center p-4">
        <div
          style={{
            transform: `scale(${zoom})`,
            transformOrigin: "center center",
          }}
          className="document-zoom max-w-full max-h-full"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={activeImage}
            alt="Passport View"
            className="rounded shadow-xl border border-zinc-800 max-h-[420px] object-contain"
          />
        </div>
      </div>

      {/* Legend */}
      {showAnnotations && annotatedImageUrl && (
        <div className="px-4 py-2 bg-zinc-950/90 border-t border-zinc-800/80 flex flex-wrap items-center gap-4 text-[11px] font-mono text-zinc-400">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500 inline-block" />
            <span>ICAO MRZ Zone</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-blue-500 inline-block" />
            <span>Portrait Face ROI</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-purple-500 inline-block" />
            <span>Visual Text Boxes</span>
          </span>
        </div>
      )}
    </div>
  );
};
