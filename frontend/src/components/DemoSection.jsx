import SectionTitle from './SectionTitle.jsx';

export default function DemoSection({
  apiBase,
  health,
  output,
  screenText,
  onApiBaseChange,
  onCheckHealth,
  onKycSubmit,
  onScreenOcrSubmit,
  onScreenTextChange,
  onScreenTextSubmit,
}) {
  return (
    <section id="demo" className="section demo-section">
      <SectionTitle eyebrow="Connected backend" title="Use Spectre APIs from the page." />
      <div className="demo-grid">
        <div className="panel api-panel">
          <label htmlFor="apiBase">Backend URL</label>
          <div className="input-row">
            <input
              id="apiBase"
              placeholder="Leave empty for Vite proxy, or set http://127.0.0.1:8000"
              value={apiBase}
              onChange={(event) => onApiBaseChange(event.target.value)}
            />
            <button onClick={onCheckHealth} type="button">Check</button>
          </div>
          <p className="status">{health}</p>
        </div>
        <form className="panel" onSubmit={onKycSubmit}>
          <h3>KYC document</h3>
          <input name="kycFile" type="file" accept="image/*,.pdf" />
          <button type="submit">Process document</button>
        </form>
        <div className="panel">
          <h3>Screen text</h3>
          <textarea value={screenText} onChange={(event) => onScreenTextChange(event.target.value)} />
          <button onClick={onScreenTextSubmit} type="button">Redact text</button>
        </div>
        <form className="panel" onSubmit={onScreenOcrSubmit}>
          <h3>Screen OCR</h3>
          <input name="screenFile" type="file" accept="image/*" />
          <button type="submit">OCR redact</button>
        </form>
      </div>
      <pre className="api-output">{output}</pre>
    </section>
  );
}
