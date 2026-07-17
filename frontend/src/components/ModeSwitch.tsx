import { ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AppMode } from "../lib/navigation";

const MODE_OPTIONS: { value: AppMode; label: string }[] = [
  { value: "user", label: "USER" },
  { value: "government", label: "OPERATOR" },
];

// Custom dropdown (not a native <select>) so the option list can be styled
// to match the rest of the monochrome UI.
export function ModeSwitch({
  appMode,
  onModeChange,
}: {
  appMode: AppMode;
  onModeChange: (mode: AppMode) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const activeLabel = MODE_OPTIONS.find((option) => option.value === appMode)?.label ?? "USER";

  return (
    <label className="mode-switch">
      <span className="mode-switch-label">Mode:</span>
      <div className="mode-switch-control" ref={containerRef}>
        <button
          type="button"
          className={`mode-switch-trigger ${isOpen ? "is-open" : ""}`}
          onClick={() => setIsOpen((open) => !open)}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
        >
          <span>{activeLabel}</span>
          <ChevronDown size={16} />
        </button>
        {isOpen && (
          <div className="mode-switch-popover" role="listbox">
            {MODE_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={option.value === appMode}
                className={`mode-switch-option ${option.value === appMode ? "active" : ""}`}
                onClick={() => {
                  onModeChange(option.value);
                  setIsOpen(false);
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </label>
  );
}
