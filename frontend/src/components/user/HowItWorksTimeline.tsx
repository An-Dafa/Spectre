const STEPS = [
  { title: "Upload or stream", description: "Pilih dokumen atau aktifkan live camera feed." },
  { title: "AI detects sensitive objects", description: "Model lokal menandai KTP, wajah, NIK, plat, dan lainnya." },
  { title: "Spectre sanitizes risky areas", description: "Area sensitif diredaksi sebelum mencapai layanan tujuan." },
  { title: "Safe output is ready to share", description: "Hasil aman siap dibagikan, original tetap terenkripsi." },
];

export function HowItWorksTimeline() {
  return (
    <div className="how-timeline">
      {STEPS.map((step, index) => (
        <div className="how-step" key={step.title}>
          <div className="how-step-marker">
            <span className="how-step-number">{index + 1}</span>
            {index < STEPS.length - 1 && <span className="how-step-line" />}
          </div>
          <div className="how-step-copy">
            <strong>{step.title}</strong>
            <p>{step.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export { STEPS as howItWorksSteps };
