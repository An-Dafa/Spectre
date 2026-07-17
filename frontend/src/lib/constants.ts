// Shared constants for Spectre frontend.

export const PRIVACY_CLASSES = ["KTP", "KK", "SIM", "Paspor", "Teks_Sensitif", "Wajah", "Plat_Nomor", "Resi"];

export const PERFORMANCE_MODES = [
  {
    value: "fast",
    label: "Fast Demo",
    description: "Recommended untuk live hackathon demo. 1x inference, tanpa OCR, tanpa heavy TTA.",
  },
  {
    value: "balanced",
    label: "Balanced",
    description: "Recommended untuk verifikasi normal. TTA 0 dan 180, OCR mati default.",
  },
  {
    value: "robust",
    label: "Robust Verification",
    description: "Untuk dokumen sulit. Lebih banyak rotasi, guardrail OCR-capable, lebih lambat.",
  },
];

// Default confidence per kelas, dikalibrasi dari kurva F1/PR per kelas model.
export const DEFAULT_CLASS_CONFIDENCE: Record<string, number> = {
  KTP: 0.35,
  KK: 0.35,
  SIM: 0.35,
  Paspor: 0.35,
  Teks_Sensitif: 0.3,
  Wajah: 0.25,
  Plat_Nomor: 0.35,
  Resi: 0.35,
};
