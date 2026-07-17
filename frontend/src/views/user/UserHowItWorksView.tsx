import { FileText, Video } from "lucide-react";

import { HowItWorksTimeline, howItWorksSteps } from "../../components/user/HowItWorksTimeline";
import { Panel } from "../../components/ui/Panel";
import { UserViewId } from "../../lib/navigation";

// import banner from "../../assets/how-it-works-banner.png";
const PAGE_ASSETS = {
  banner: "" as string,
};

const DETAILS = [
  "Choose a tool: upload a document (JPG/PNG/WEBP/PDF) or run the Live Stream Privacy Filter from the camera. Both stay inside Spectre's privacy boundary.",
  "The Spectre detection model scans input and marks sensitive objects: IDs, passports, sensitive text, faces, and license plates. Each class has a calibrated confidence threshold.",
  "Risky areas are visually redacted immediately (black box, blur, or pixelate). False-positive guardrails filter doubtful detections before final redaction.",
  "Redacted output is ready to share safely. The original document is encrypted into the Sovereign Vault, while the Operational Zone stores only redacted output and non-private metadata.",
];

export function UserHowItWorksView({ onNavigate }: { onNavigate: (view: UserViewId) => void }) {
  return (
    <div className="user-page">
      {PAGE_ASSETS.banner && <img className="page-banner" src={PAGE_ASSETS.banner} alt="" />}
      <section className="user-hero user-hero-compact">
        <div className="user-hero-copy">
          <h1>How Spectre works.</h1>
          <p>Four simple steps, from raw input to safe shareable output.</p>
        </div>
      </section>

      <section className="user-section">
        <HowItWorksTimeline />
      </section>

      <section className="user-section">
        <div className="how-detail-list">
          {howItWorksSteps.map((step, index) => (
            <article className="how-detail-card" key={step.title}>
              <span className="how-detail-number">{index + 1}</span>
              <div>
                <strong>{step.title}</strong>
                <p>{DETAILS[index]}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <Panel title="Ready to try?" eyebrow="Start" icon={<FileText />}>
        <div className="button-row">
          <button type="button" className="primary-button" onClick={() => onNavigate("document-upload")}>
            <FileText size={16} /> Document Upload
          </button>
          <button
            type="button"
            className="primary-button secondary-button"
            onClick={() => onNavigate("live-filter")}
          >
            <Video size={16} /> Start Live Filter
          </button>
        </div>
      </Panel>
    </div>
  );
}
