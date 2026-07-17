import { FileText, Video } from "lucide-react";

import { HowItWorksTimeline, howItWorksSteps } from "../../components/user/HowItWorksTimeline";
import { Panel } from "../../components/ui/Panel";
import { UserViewId } from "../../lib/navigation";

// ╔═══ ASSET PAGE INI — ubah di sini ═══╗
// Taruh file di src/assets/ lalu uncomment import & isi nama file.
// import banner from "../../assets/how-it-works-banner.png";
const PAGE_ASSETS = {
  banner: "" as string, // banner gambar di atas halaman; "" = tidak ditampilkan
};
// ╚══════════════════════════════════════╝

const DETAILS = [
  "Pilih salah satu tool: unggah dokumen (JPG/PNG/WEBP/PDF satu halaman) atau jalankan Live Stream Privacy Filter dari kamera. Keduanya diproses di dalam privacy boundary Spectre.",
  "Model deteksi Spectre memindai input dan menandai objek sensitif: KTP, SIM, Paspor, teks NIK, wajah, dan plat nomor. Tiap kelas punya ambang confidence yang dikalibrasi.",
  "Area berisiko langsung diredaksi secara visual (black box, blur, atau pixelate). Guardrail false-positive menyaring deteksi yang meragukan sebelum redaksi final.",
  "Hasil tersensor siap dibagikan dengan aman. Dokumen original dienkripsi ke Sovereign Vault, sementara Operational Zone hanya menyimpan output tersensor dan metadata non-privat.",
];

export function UserHowItWorksView({ onNavigate }: { onNavigate: (view: UserViewId) => void }) {
  return (
    <div className="user-page">
      {PAGE_ASSETS.banner && <img className="page-banner" src={PAGE_ASSETS.banner} alt="" />}
      <section className="user-hero user-hero-compact">
        <div className="user-hero-copy">
          <h1>How Spectre works.</h1>
          <p>Empat langkah sederhana, dari input mentah sampai output yang aman dibagikan.</p>
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

      <Panel title="Siap mencoba?" eyebrow="Mulai" icon={<FileText />}>
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
