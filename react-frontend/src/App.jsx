import { useState, useCallback } from "react";
import StepBar from "./components/StepBar.jsx";
import PaymentForm from "./components/PaymentForm.jsx";
import SuccessScreen from "./components/SuccessScreen.jsx";
import FailedScreen from "./components/FailedScreen.jsx";
import ApiTestPanel from "./components/ApiTestPanel.jsx";

export default function App() {
  const [step, setStep] = useState(1);
  const [result, setResult] = useState(null);
  const [failed, setFailed] = useState(null);
  const [showApiPanel, setShowApiPanel] = useState(false);

  const handleSuccess = useCallback((data) => {
    setResult(data);
    setStep(3);
  }, []);

  const handleReset = useCallback(() => {
    setStep(1);
    setResult(null);
    setFailed(null);
  }, []);

  return (
    <>
      <div className="bg-orbs">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
      </div>

      <main className="page">
        <header className="header">
          <div className="logo">
            <div className="logo-icon">💳</div>
            <span className="logo-text">SecurePay</span>
          </div>
          <p className="header-sub">Powered by Razorpay · Secure Mode</p>
        </header>

        <StepBar step={step} />

        {step === 1 && <PaymentForm onSuccess={handleSuccess} />}
        {step === 3 && result && <SuccessScreen data={result} onReset={handleReset} />}
        {step === 3 && !result && failed && <FailedScreen reason={failed} onReset={handleReset} />}

        <footer className="footer">
          <span className="footer-badge">🔒 256-bit SSL Encrypted</span>
          <span>·</span>
          <span className="footer-badge">🛡️ PCI DSS Compliant</span>
        </footer>
      </main>

      <button
        className="api-test-toggle"
        onClick={() => setShowApiPanel(true)}
        title="Open API Test Panel"
      >
        <span className="dot" />
        🧪 API Test
      </button>

      {showApiPanel && (
        <ApiTestPanel onClose={() => setShowApiPanel(false)} />
      )}
    </>
  );
}
