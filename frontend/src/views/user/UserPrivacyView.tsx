import { Cpu, Database, EyeOff, LockKeyhole } from "lucide-react";

import { Panel } from "../../components/ui/Panel";

// ╔═══ ASSET PAGE INI — ubah di sini ═══╗
// Taruh file di src/assets/ lalu uncomment import & isi nama file.
// import banner from "../../assets/privacy-banner.png";
const PAGE_ASSETS = {
  banner: "" as string, // banner gambar di atas halaman; "" = tidak ditampilkan
};
// ╚══════════════════════════════════════╝

const FLOW = [
  {
    icon: <Cpu size={22} />,
    title: "Local AI Detection",
    description:
      "Deteksi objek sensitif berjalan di backend lokal kamu. Gambar tidak dikirim ke layanan pihak ketiga untuk dianalisis.",
  },
  {
    icon: <EyeOff size={22} />,
    title: "Visual Redaction",
    description:
      "Area berisiko (KTP, wajah, NIK, plat nomor) diredaksi secara visual sebelum hasil meninggalkan perangkat.",
  },
  {
    icon: <Database size={22} />,
    title: "Operational Metadata",
    description:
      "Hanya hasil tersensor dan metadata non-privat yang disimpan di Operational Zone. Original tidak pernah disimpan di sana.",
  },
  {
    icon: <LockKeyhole size={22} />,
    title: "Encrypted Sovereign Vault",
    description:
      "Dokumen original dienkripsi (AES-256-GCM) dan disimpan di Sovereign Vault. Aksesnya hanya lewat jalur otorisasi resmi.",
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
            Spectre dibangun supaya data identitas kamu terlindungi di setiap langkah &mdash; dari deteksi sampai
            penyimpanan terenkripsi.
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

      <Panel title="Apa yang TIDAK dilakukan Spectre" eyebrow="Transparansi" icon={<LockKeyhole />}>
        <ul className="privacy-list">
          <li>Tidak menyimpan dokumen original di area yang bisa diakses umum.</li>
          <li>Tidak mengirim private key ke User Zone maupun Operational Zone.</li>
          <li>Tidak memberi akses original tanpa request, approval, dan token sekali pakai.</li>
          <li>Tidak menjalankan kode arbitrer &mdash; runtime policy hanya konfigurasi tervalidasi.</li>
        </ul>
      </Panel>
    </div>
  );
}
