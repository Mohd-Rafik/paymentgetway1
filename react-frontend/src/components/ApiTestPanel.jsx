import { useState, useCallback } from "react";

const ENDPOINTS = [
  {
    id: "health",
    method: "GET",
    path: "/",
    desc: "Health Check",
    body: null,
    pathParam: null,
  },
  {
    id: "create-invoice",
    method: "POST",
    path: "/api/payment/create-invoice",
    desc: "Create Invoice",
    pathParam: null,
    body: JSON.stringify(
      {
        name: "Rafik Ahmed",
        email: "rafik@example.com",
        address: "123 Street, Hyderabad",
        amount: 499.00,
      },
      null,
      2
    ),
  },
  {
    id: "verify-payment",
    method: "POST",
    path: "/api/payment/verify-payment",
    desc: "Verify Payment",
    pathParam: null,
    body: JSON.stringify(
      {
        razorpay_order_id: "order_XXXXXXXXXXXXX",
        razorpay_payment_id: "pay_XXXXXXXXXXXXX",
        razorpay_signature: "your_signature_here",
      },
      null,
      2
    ),
  },
  {
    id: "payment-failed",
    method: "POST",
    path: "/api/payment/payment-failed",
    desc: "Mark Payment Failed",
    pathParam: null,
    body: JSON.stringify(
      {
        razorpay_order_id: "order_XXXXXXXXXXXXX",
        reason: "User dismissed checkout",
      },
      null,
      2
    ),
  },
  {
    id: "get-transaction",
    method: "GET",
    path: "/api/payment/transaction",
    desc: "Fetch Transaction",
    pathParam: "order_XXXXXXXXXXXXX",
    body: null,
  },
];

function EndpointCard({ ep, baseUrl }) {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState(ep.body || "");
  const [pathParam, setPathParam] = useState(ep.pathParam || "");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);

  const handleSend = useCallback(async () => {
    setLoading(true);
    setResponse(null);

    let url = baseUrl + ep.path;
    if (ep.pathParam !== null) {
      url = `${url}/${pathParam}`;
    }

    const opts = {
      method: ep.method,
      headers: { "Content-Type": "application/json" },
    };

    if (ep.method === "POST" && body.trim()) {
      try {
        JSON.parse(body);
        opts.body = body;
      } catch {
        setResponse({ status: "Error", ok: false, json: { error: "Invalid JSON in request body" } });
        setLoading(false);
        return;
      }
    }

    try {
      const res = await fetch(url, opts);
      let json;
      try {
        json = await res.json();
      } catch {
        json = { raw: await res.text() };
      }
      setResponse({ status: res.status, ok: res.ok, json });
    } catch (err) {
      setResponse({
        status: "Network Error",
        ok: false,
        json: { error: err.message, hint: "Is the backend running? Check CORS." },
      });
    } finally {
      setLoading(false);
    }
  }, [ep, baseUrl, body, pathParam]);

  return (
    <div className="ep-card">
      <div className="ep-header" onClick={() => setOpen((o) => !o)}>
        <span className={`ep-method ${ep.method.toLowerCase()}`}>{ep.method}</span>
        <span className="ep-path">
          {ep.path}
          {ep.pathParam !== null ? "/{id}" : ""}
        </span>
        <span className="ep-desc">{ep.desc}</span>
        <span className={`ep-chevron ${open ? "open" : ""}`}>▼</span>
      </div>

      {open && (
        <div className="ep-body">
          {ep.pathParam !== null && (
            <div>
              <div className="ep-textarea-label">Path Parameter (Order ID)</div>
              <input
                className="ep-path-input"
                value={pathParam}
                onChange={(e) => setPathParam(e.target.value)}
                placeholder="order_XXXXXXXXXXXXX"
              />
            </div>
          )}

          {ep.method === "POST" && (
            <div>
              <div className="ep-textarea-label">Request Body (JSON)</div>
              <textarea
                className="ep-textarea"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={6}
                spellCheck={false}
              />
            </div>
          )}

          <button className="ep-send-btn" onClick={handleSend} disabled={loading}>
            {loading ? (
              <>
                <span className="mini-spinner" /> Sending…
              </>
            ) : (
              <>▶ Send Request</>
            )}
          </button>

          {response && (
            <div className={`ep-response ${response.ok ? "ok" : "fail"}`}>
              <div className="ep-response-meta">
                <span>{response.ok ? "✓" : "✗"}</span>
                <span className="status-badge">
                  Status: {response.status}
                </span>
                <span style={{ marginLeft: "auto", opacity: 0.7 }}>
                  {response.ok ? "Success" : "Failed"}
                </span>
              </div>
              <pre className="ep-response-body">
                {JSON.stringify(response.json, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ApiTestPanel({ onClose }) {
  const [baseUrl, setBaseUrl] = useState(
    import.meta.env.VITE_API_URL || "http://localhost:8000"
  );

  return (
    <div className="api-panel-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="api-panel">
        <div className="api-panel-header">
          <div className="api-panel-title">
            <span>🧪</span>
            <div>
              <h2>API Test Panel</h2>
              <span>Test all endpoints</span>
            </div>
          </div>
          <button className="api-panel-close" onClick={onClose} title="Close">✕</button>
        </div>

        <div className="base-url-bar">
          <span>Base URL</span>
          <input
            className="base-url-input"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value.replace(/\/$/, ""))}
            placeholder="http://localhost:8000"
          />
        </div>

        <div className="api-panel-body">
          {ENDPOINTS.map((ep) => (
            <EndpointCard key={ep.id} ep={ep} baseUrl={baseUrl} />
          ))}
        </div>
      </div>
    </div>
  );
}