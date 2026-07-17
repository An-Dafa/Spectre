import { ArrowRight } from "lucide-react";
import { ReactNode } from "react";

export function ToolCard({
  title,
  description,
  ctaLabel,
  icon,
  accent,
  image,
  imageAlt = "",
  onClick,
}: {
  title: string;
  description: string;
  ctaLabel: string;
  icon: ReactNode;
  accent: "blue" | "copper";
  image?: string;
  imageAlt?: string;
  onClick: () => void;
}) {
  return (
    <button type="button" className={`tool-card tool-card-${accent}`} onClick={onClick}>
      <div className="tool-card-body">
        <div className="tool-card-icon">{icon}</div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      {image && <img className="tool-card-image" src={image} alt={imageAlt} aria-hidden={!imageAlt} />}
      <span className="tool-card-cta">
        {ctaLabel}
        <ArrowRight size={16} />
      </span>
    </button>
  );
}
