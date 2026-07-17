export default function TracksSection() {
  return (
    <section id="tracks" className="section split-section">
      <div className="large-card">
        <p className="eyebrow">AI you can audit</p>
        <h2>Built for privacy boundaries, not just uploads.</h2>
        <p>
          Every track shows the same promise: raw input stays on the unsafe side, Spectre performs the privacy pass,
          and destinations only receive safe output.
        </p>
        <div className="mini-flow" aria-label="Spectre processing flow">
          <span>Detect</span>
          <span>Validate</span>
          <span>Redact</span>
          <span>Audit</span>
        </div>
      </div>
      <div className="side-card">
        <h3>Runs where you decide</h3>
        <ul>
          <li>Local YOLO model path</li>
          <li>Sovereign Vault encryption</li>
          <li>Runtime policy injection</li>
          <li>ScreenShield OCR pass</li>
        </ul>
      </div>
    </section>
  );
}
