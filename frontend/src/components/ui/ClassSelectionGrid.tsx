export function ClassSelectionGrid({
  options,
  selected,
  onChange,
  helper,
}: {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  helper?: string;
}) {
  const normalizedSelected = options.filter((option) => selected.includes(option));

  function toggleOption(option: string) {
    const nextSelected = normalizedSelected.includes(option)
      ? normalizedSelected.filter((item) => item !== option)
      : [...normalizedSelected, option];
    onChange(options.filter((item) => nextSelected.includes(item)));
  }

  return (
    <div className="class-toggle-panel">
      <div className="class-toggle-toolbar">
        <span>
          {normalizedSelected.length} of {options.length} classes active
        </span>
        <div>
          <button type="button" className="text-button" onClick={() => onChange([...options])}>
            Select All
          </button>
          <button type="button" className="text-button" onClick={() => onChange([])}>
            Clear
          </button>
        </div>
      </div>
      <div className="class-toggle-grid">
        {options.map((option) => {
          const isActive = normalizedSelected.includes(option);
          return (
            <button
              key={option}
              type="button"
              className={`class-toggle-card ${isActive ? "active" : ""}`}
              onClick={() => toggleOption(option)}
              aria-pressed={isActive}
            >
              <strong>{option}</strong>
              <small>{isActive ? "Active" : "Inactive"}</small>
            </button>
          );
        })}
      </div>
      {helper && <small className="field-hint">{helper}</small>}
      {normalizedSelected.length === 0 && (
        <small className="field-warning">No active classes. Redaction results may be empty.</small>
      )}
    </div>
  );
}
