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
          {normalizedSelected.length} dari {options.length} kelas aktif
        </span>
        <div>
          <button type="button" className="text-button" onClick={() => onChange([...options])}>
            Pilih Semua
          </button>
          <button type="button" className="text-button" onClick={() => onChange([])}>
            Kosongkan
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
              <small>{isActive ? "Aktif" : "Nonaktif"}</small>
            </button>
          );
        })}
      </div>
      {helper && <small className="field-hint">{helper}</small>}
      {normalizedSelected.length === 0 && (
        <small className="field-warning">Tidak ada kelas aktif. Hasil redaksi bisa kosong.</small>
      )}
    </div>
  );
}
