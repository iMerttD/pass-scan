import React from "react";
import { ScanLine, RotateCcw } from "lucide-react";

interface HeaderProps {
  onReset?: () => void;
  hasActiveSession?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onReset, hasActiveSession }) => {
  return (
    <header className="workspace-header">
      <a className="skip-link" href="#main-content">Skip to workspace</a>
      <div className="workspace-brand"><ScanLine size={24} /><div><strong>Passport<span>Office</span></strong><small>DOCUMENT VERIFICATION</small></div></div>
      <div className="workspace-header__content">
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm sm:text-base font-bold text-zinc-100 tracking-tight">
                Examination workspace
              </span>
            </div>
            <p className="hidden text-xs text-zinc-400 sm:block">
              Passport intake and operator review
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">

          {hasActiveSession && onReset && (
            <button
              onClick={onReset}
              aria-label="Start a new examination"
              className="office-button office-button--secondary"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">New Examination</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
