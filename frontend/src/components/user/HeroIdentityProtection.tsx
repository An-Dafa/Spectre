import { ArrowRight } from "lucide-react";

// Black rounded hero from the Figma user dashboard. Before / After visuals fall
// back to CSS placeholders when no image is provided. Pass image paths from the
// parent page (see PAGE_ASSETS in UserHomeView.tsx).
export function HeroIdentityProtection({
  beforeImage = "../../assets/smiling.png",
  afterImage = "../../assets/smiling.png",
}: {
  beforeImage?: string;
  afterImage?: string;
}) {
  return (
    <section className="user-hero">
      <div className="user-hero-copy">
        <h1>Protect your identity before it reaches the destination.</h1>
        <p>
          Spectre detects sensitive identity information inside a controlled privacy boundary, then delivers only the
          protected visual output for operational use.
        </p>
      </div>
      <div className="user-hero-visual">
        <figure className="hero-shot">
          <span className="hero-shot-label">Before</span>
          <div className="hero-shot-frame hero-shot-before" aria-hidden="true">
            {beforeImage ? <img src={beforeImage} alt="" /> : <div className="hero-face" />}
          </div>
        </figure>
        <ArrowRight className="hero-arrow" size={32} style={{ marginTop: '14px' }} />
        <figure className="hero-shot">
          <span className="hero-shot-label">After</span>
          <div className="hero-shot-frame hero-shot-after" aria-hidden="true">
            {afterImage ? <img src={afterImage} alt="" /> : <div className="hero-face hero-face-blurred" />}
          </div>
        </figure>
      </div>
    </section>
  );
}
