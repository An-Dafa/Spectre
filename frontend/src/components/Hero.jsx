import { institutions } from '../data/content.js';

export default function Hero() {
  return (
    <section id="hero" className="hero">
      <div className="hero-copy">
        <h1><span>AI privacy workflows</span> you can see and control</h1>
        <div className="actions">
          <a className="button primary" href="#demo">Get started for free</a>
          <a className="button secondary" href="#bridge">Talk to team</a>
        </div>
        <p>
          Build visual privacy pipelines, connect detection models, and redact sensitive data before it reaches
          operational storage, broadcasts, or screen-share transports.
        </p>
        <div className="hero-trust">
          <p>Trusted privacy middleware for teams including</p>
          <div>
            {institutions.slice(0, 4).map((name) => <span key={name}>{name}</span>)}
          </div>
        </div>
      </div>
      <HeroGraphic />
    </section>
  );
}

function HeroGraphic() {
  return (
    <div className="hero-graphic" aria-label="Spectre data security visual">
      <div className="security-visual">
        <div className="data-card data-card-a">
          <span />
          <span />
          <span />
        </div>
        <div className="lock-core">
          <span className="lock-shackle" />
          <span className="lock-body">
            <i />
          </span>
        </div>
        <div className="data-card data-card-b">
          <span />
          <span />
          <span />
        </div>
        <div className="data-line line-a" />
        <div className="data-line line-b" />
      </div>
    </div>
  );
}
