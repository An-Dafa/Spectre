import { FileText, Video } from "lucide-react";

import femaleImage from "../../assets/female.png";
import maleImage from "../../assets/male.png";
import smilingImage from "../../assets/smiling.png";
import { HeroIdentityProtection } from "../../components/user/HeroIdentityProtection";
import { HowItWorksTimeline } from "../../components/user/HowItWorksTimeline";
import { ToolCard } from "../../components/user/ToolCard";
import { UserViewId } from "../../lib/navigation";

const PAGE_ASSETS = {
  heroBefore: smilingImage,
  heroAfter: smilingImage,
  documentTool: maleImage,
  liveTool: femaleImage,
};

export function UserHomeView({ onNavigate }: { onNavigate: (view: UserViewId) => void }) {
  return (
    <div className="user-page">
      <HeroIdentityProtection beforeImage={PAGE_ASSETS.heroBefore} afterImage={PAGE_ASSETS.heroAfter} />

      <section className="user-section">
        <div className="user-section-head">
          <span className="user-section-line" />
          <h2>Tools</h2>
          <span className="user-section-line" />
        </div>
        <div className="tool-card-grid">
          <ToolCard
            title="Document Privacy Shield"
            description="Unggah dokumen identitas dan biarkan Spectre meredaksi area sensitif sebelum dibagikan."
            ctaLabel="Document Upload"
            accent="blue"
            icon={<FileText size={24} />}
            image={PAGE_ASSETS.documentTool}
            imageAlt=""
            onClick={() => onNavigate("document-upload")}
          />
          <ToolCard
            title="Live Stream Privacy Filter"
            description="Aktifkan filter privasi real-time untuk feed kamera langsung dari perangkat."
            ctaLabel="Start Live Filter"
            accent="copper"
            icon={<Video size={24} />}
            image={PAGE_ASSETS.liveTool}
            imageAlt=""
            onClick={() => onNavigate("live-filter")}
          />
        </div>
      </section>

      <section className="user-section">
        <div className="user-section-head">
          <span className="user-section-line" />
          <h2>How It Works</h2>
          <span className="user-section-line" />
        </div>
        <HowItWorksTimeline />
      </section>
    </div>
  );
}
