import { institutions } from '../data/content.js';
import SectionTitle from './SectionTitle.jsx';

export default function IntegrationsSection() {
  return (
    <section id="integrations" className="section">
      <SectionTitle
        eyebrow="Plug Spectre into institutions"
        title="Connect AI privacy to services people already trust."
        text="Dummy institution marks for now. Replace these with official partner logos when the final assets arrive."
      />
      <div className="integration-grid">
        {institutions.map((name) => (
          <div className="integration" key={name}>
            <span>{name.slice(0, 3).toUpperCase()}</span>
            <strong>{name}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
