export default function FailedScreen({ reason, onReset }) {
  return (
    <div className="card result-card">
      <div className="result-icon failed">✗</div>
      <h2 className="result-title failed">Payment Failed</h2>
      <p className="result-msg">
        {reason || "Something went wrong with your payment."}<br />
        Please try again or use a different payment method.
      </p>
      <button id="btn-retry" className="btn btn-error" onClick={onReset}>
        ↺ Try Again
      </button>
    </div>
  );
}
