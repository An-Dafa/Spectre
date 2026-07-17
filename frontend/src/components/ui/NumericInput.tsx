import { useEffect, useRef, useState } from "react";

export function NumericInput({
  value,
  fallbackValue,
  onValueChange,
  min,
  max,
  step,
}: {
  value: number;
  fallbackValue: number;
  onValueChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  const [draft, setDraft] = useState(String(value));
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (document.activeElement !== inputRef.current) {
      setDraft(String(value));
    }
  }, [value]);

  function commitValue() {
    const rawValue = draft.trim() === "" ? fallbackValue : Number(draft);
    let nextValue = Number.isFinite(rawValue) ? rawValue : fallbackValue;
    if (typeof min === "number") nextValue = Math.max(min, nextValue);
    if (typeof max === "number") nextValue = Math.min(max, nextValue);
    setDraft(String(nextValue));
    onValueChange(nextValue);
  }

  return (
    <input
      ref={inputRef}
      type="number"
      min={min}
      max={max}
      step={step}
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={commitValue}
    />
  );
}
