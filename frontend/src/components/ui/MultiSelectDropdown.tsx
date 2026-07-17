import { ChevronDown, ChevronRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export function MultiSelectDropdown({
  options,
  selected,
  onChange,
  label,
}: {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  label: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const normalizedSelected = options.filter((option) => selected.includes(option));

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const toggleOption = (opt: string) => {
    const next = normalizedSelected.includes(opt)
      ? normalizedSelected.filter((item) => item !== opt)
      : [...normalizedSelected, opt];
    onChange(options.filter((option) => next.includes(option)));
  };

  return (
    <div className="multi-select-container" ref={containerRef}>
      <button type="button" className="multi-select-trigger" onClick={() => setIsOpen(!isOpen)}>
        <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {normalizedSelected.length === 0
            ? `Pilih ${label}...`
            : normalizedSelected.length <= 2
              ? normalizedSelected.join(", ")
              : `${normalizedSelected.length} ${label} dipilih`}
        </span>
        {isOpen ? (
          <ChevronDown size={16} style={{ flexShrink: 0 }} />
        ) : (
          <ChevronRight size={16} style={{ flexShrink: 0 }} />
        )}
      </button>
      {isOpen && (
        <div className="multi-select-popover">
          {options.map((opt) => (
            <button key={opt} type="button" className="multi-select-option" onClick={() => toggleOption(opt)}>
              <input type="checkbox" checked={normalizedSelected.includes(opt)} readOnly tabIndex={-1} />
              <span>{opt}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
