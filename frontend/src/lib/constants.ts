// Shared constants for Spectre frontend.

export const PRIVACY_CLASSES = ["KTP", "SIM", "Paspor", "NIK_Teks", "Wajah", "Plat_Nomor"];

export const PERFORMANCE_MODES = [
  {
    value: "fast",
    label: "Fast Demo",
    description: "Recommended for live demo use. One inference pass, no OCR, no heavy TTA.",
  },
  {
    value: "balanced",
    label: "Balanced",
    description: "Recommended for normal verification. TTA 0 and 180, OCR off by default.",
  },
  {
    value: "robust",
    label: "Robust Verification",
    description: "For difficult documents. More rotations, OCR-capable guardrail, slower processing.",
  },
];

// Default confidence per class, calibrated from the model F1/PR curve.
export const DEFAULT_CLASS_CONFIDENCE: Record<string, number> = {
  KTP: 0.35,
  SIM: 0.35,
  Paspor: 0.35,
  NIK_Teks: 0.3,
  Wajah: 0.25,
  Plat_Nomor: 0.35,
};
