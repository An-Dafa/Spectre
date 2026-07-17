import SectionTitle from './SectionTitle.jsx';
import { tracks } from '../data/content.js';

export default function BridgeSection({ activeTrack, setActiveTrack, track }) {
  return (
    <section id="bridge" className="section">
      <SectionTitle eyebrow="The Bridge Layout" title="Raw data enters. Spectre decides what can leave." />
      <div className="track-tabs" role="tablist" aria-label="Spectre tracks">
        {Object.entries(tracks).map(([key, item]) => (
          <button
            className={`tab ${activeTrack === key ? 'active' : ''}`}
            key={key}
            onClick={() => setActiveTrack(key)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>
      <Bridge track={track} />
    </section>
  );
}

function Bridge({ track }) {
  return (
    <div className="bridge-canvas">
      <article className="bridge-node">
        <span className="node-label">Source / unsafe</span>
        <h3>{track.source.split('.')[0]}</h3>
        <p>{track.source}</p>
        <div className="sample-card danger">
          <small>RAW DATA</small>
          <strong>Visible sensitive fields</strong>
        </div>
      </article>
      <div className="connector" />
      <article className="bridge-node engine">
        <span className="node-label">Spectre Edge Engine</span>
        <h3>{track.label}</h3>
        <ul>
          {track.engine.map((item) => <li key={item}>{item}</li>)}
        </ul>
        <div className="endpoint">{track.endpoint}</div>
      </article>
      <div className="connector" />
      <article className="bridge-node">
        <span className="node-label">Destination / safe</span>
        <h3>Redacted destination</h3>
        <p>{track.destination}</p>
        <div className="sample-card safe-card">
          <small>SAFE OUTPUT</small>
          <strong>No raw identity data</strong>
        </div>
      </article>
    </div>
  );
}
