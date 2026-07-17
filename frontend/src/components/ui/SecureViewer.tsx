import { EyeOff, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

export function SecureViewer({
  url,
  title,
  onClose,
  isSensitive,
}: {
  url: string;
  title: string;
  onClose: () => void;
  isSensitive: boolean;
}) {
  const [isBlurred, setIsBlurred] = useState(false);

  useEffect(() => {
    const handleBlur = () => {
      if (isSensitive) setIsBlurred(true);
    };
    const handleFocus = () => {
      if (isSensitive) setIsBlurred(false);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      // Basic anti-screenshot best effort
      if (e.key === "PrintScreen" || (e.metaKey && e.shiftKey && (e.key === "s" || e.key === "S" || e.key === "3" || e.key === "4"))) {
        if (isSensitive) {
          setIsBlurred(true);
          setTimeout(() => setIsBlurred(false), 3000);
        }
      }
    };

    window.addEventListener("blur", handleBlur);
    window.addEventListener("focus", handleFocus);
    document.addEventListener("keydown", handleKeyDown);

    // Disable right click globally while viewer is open if sensitive
    const preventContext = (e: MouseEvent) => {
      if (isSensitive) e.preventDefault();
    };
    document.addEventListener("contextmenu", preventContext);

    return () => {
      window.removeEventListener("blur", handleBlur);
      window.removeEventListener("focus", handleFocus);
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("contextmenu", preventContext);
    };
  }, [isSensitive]);

  return (
    <div className="secure-modal-backdrop">
      <div className="secure-modal-content">
        <div className="secure-modal-header">
          <h3>
            {isSensitive ? <ShieldCheck size={20} /> : <EyeOff size={20} />} {title}
          </h3>
          <button className="secondary-button" style={{ padding: "6px 16px", borderRadius: "8px" }} onClick={onClose}>
            Tutup
          </button>
        </div>
        <div className="secure-modal-body" onContextMenu={(e) => { if (isSensitive) e.preventDefault(); }}>
          <div className="secure-image-container">
            <img src={url} className={`secure-image ${isBlurred ? "secure-blur" : ""}`} draggable="false" />
            {isSensitive && (
              <div className="secure-watermark">
                CONFIDENTIAL • CONFIDENTIAL • CONFIDENTIAL<br />
                RESTRICTED GOVERNMENT ACCESS ONLY
              </div>
            )}
          </div>
          <p style={{ color: "#888", marginTop: "16px", fontSize: "13px", textAlign: "center" }}>
            {isSensitive
              ? "Tangkap layar (Screenshot) dan klik kanan dilarang. Aktivitas ini dipantau secara ketat."
              : "Mode pratinjau gambar."}
          </p>
        </div>
      </div>
    </div>
  );
}
