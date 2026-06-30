export default function StepBar({ step }) {
  const steps = ["Details", "Payment", "Done"];
  return (
    <div className="steps">
      {steps.map((label, i) => {
        const idx = i + 1;
        const isActive = step === idx;
        const isDone = step > idx;
        return (
          <div key={label} className="step-item">
            <div className={`step-dot ${isActive ? "active" : ""} ${isDone ? "done" : ""}`}>
              {isDone ? "✓" : idx}
            </div>
            <span className={`step-label ${isActive ? "active" : ""} ${isDone ? "done" : ""}`}>
              {label}
            </span>
            {i < steps.length - 1 && (
              <div className={`step-line ${isDone ? "done" : ""}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
