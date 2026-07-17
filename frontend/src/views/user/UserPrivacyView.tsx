import { Cpu, Database, EyeOff, LockKeyhole } from "lucide-react";

import { Panel } from "../../components/ui/Panel";

// import banner from "../../assets/privacy-banner.png";
const PAGE_ASSETS = {
  banner: "" as string,
};

const FLOW = [
  {
    icon: <Cpu size={22} />,
    title: "Local AI Detection",
    description:
      "Sensitive object detection runs on your local backend. Images are not sent to third-party services for analysis.",
  },
  {
    icon: <EyeOff size={22} />,
    title: "Visual Redaction",
    description:
      "Risky areas such as IDs, faces, sensitive text, and license plates are visually redacted before output leaves the device.",
  },
  {
    icon: <Database size={22} />,
    title: "Operational Metadata",
    description:
      "Only redacted output and non-private metadata are stored in the Operational Zone. The original is never stored there.",
  },
  {
    icon: <LockKeyhole size={22} />,
    title: "Encrypted Sovereign Vault",
    description:
      "Original documents are encrypted with AES-256-GCM and stored in the Sovereign Vault. Access is only available through an official authorization path.",
  },
];

export function UserPrivacyView() {
  return (
    <div className="user-page">
      {PAGE_ASSETS.banner && <img className="page-banner" src={PAGE_ASSETS.banner} alt="" />}
      <section className="user-hero user-hero-compact">
        <div className="user-hero-copy">
          <h1>Privacy-first by design.</h1>
          <p>
            Spectre is built to keep identity data protected at every step, from detection to encrypted storage.
          </p>
        </div>
      </section>

      <section className="user-section">
        <div className="privacy-flow-grid">
          {FLOW.map((item) => (
            <article className="privacy-flow-card" key={item.title}>
              <div className="tool-card-icon">{item.icon}</div>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <Panel title="What Spectre Does Not Do" eyebrow="Transparency" icon={<LockKeyhole />}>
        <ul className="privacy-list">
          <li>Does not store original documents in broadly accessible areas.</li>
          <li>Does not send private keys to the User Zone or Operational Zone.</li>
          <li>Does not provide original access without a request, approval, and one-time token.</li>
          <li>Does not execute arbitrary code. Runtime policy is validated configuration only.</li>
        </ul>
      </Panel>
    </div>
  );
}
