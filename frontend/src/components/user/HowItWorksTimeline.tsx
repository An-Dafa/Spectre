const STEPS = [
  { title: "Upload or stream", description: "Choose a document or enable the live camera feed." },
  { title: "AI detects sensitive objects", description: "The local model marks IDs, faces, sensitive text, plates, and more." },
  { title: "Spectre sanitizes risky areas", description: "Sensitive areas are redacted before reaching the destination service." },
  { title: "Safe output is ready to share", description: "Safe output is ready to share while the original stays encrypted." },
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
