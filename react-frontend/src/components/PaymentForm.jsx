import { useState, useCallback } from "react";
import { createInvoice, verifyPayment, markPaymentFailed } from "../api.js";

export default function PaymentForm({ onSuccess }) {
  const [form, setForm] = useState({ name: "", email: "", address: "", amount: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [invoice, setInvoice] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleGenerateInvoice = useCallback(async (e) => {
    e.preventDefault();
    setError("");

    const amt = parseFloat(form.amount);
    if (!form.name.trim()) return setError("Please enter your name.");
    if (!form.email.includes("@")) return setError("Please enter a valid email.");
    if (isNaN(amt) || amt <= 0) return setError("Please enter a valid amount.");

    setLoading(true);
    try {
      const invoiceData = await createInvoice({
        name: form.name.trim(),
        email: form.email.trim(),
        address: form.address.trim(),
        amount: amt,
      });
      setInvoice(invoiceData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [form]);

  const handlePayNow = useCallback(() => {
    if (!invoice) return;
    setError("");
    setLoading(true);

    const options = {
      key: invoice.keyId,
      amount: invoice.amount,
      currency: invoice.currency,
      order_id: invoice.razorpayOrderId,
      name: "SecurePay",
      description: "Secure Payment",
      prefill: { name: form.name, email: form.email, contact: "" },
      theme: { color: "#7c3aed" },
      handler: async (response) => {
        try {
          const result = await verifyPayment({
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          });
          onSuccess({
            orderId: invoice.razorpayOrderId,
            paymentId: response.razorpay_payment_id,
            paymentMethod: result.paymentMethod,
            invoiceUrl: invoice.shortUrl,
            amount: parseFloat(form.amount),
            name: form.name,
            email: form.email,
          });
        } catch (err) {
          setError("Verification failed: " + err.message);
          setLoading(false);
        }
      },
      modal: {
        ondismiss: async () => {
          await markPaymentFailed(invoice.razorpayOrderId, "User dismissed checkout");
          setError("Payment cancelled. You can try again.");
          setLoading(false);
        },
      },
    };

    if (typeof window.Razorpay === "undefined") {
      setError("Razorpay SDK not loaded. Please refresh the page.");
      setLoading(false);
      return;
    }
    const rzp = new window.Razorpay(options);
    rzp.on("payment.failed", async (resp) => {
      await markPaymentFailed(invoice.razorpayOrderId, resp.error?.description || "Payment failed");
      setError("Payment failed: " + (resp.error?.description || "Unknown error"));
      setLoading(false);
    });
    rzp.open();
    setLoading(false);
  }, [invoice, form, onSuccess]);

  const handleEditDetails = () => {
    setInvoice(null);
    setError("");
  };

  if (invoice) {
    return (
      <div className="card">
        <h2 className="card-title">Invoice Generated ✅</h2>
        <p className="card-subtitle">Review your invoice and proceed to payment</p>

        <div className="txn-details">
          <div className="txn-row">
            <span className="txn-key">Invoice ID</span>
            <span className="txn-val">{invoice.invoiceId}</span>
          </div>
          <div className="txn-row">
            <span className="txn-key">Order ID</span>
            <span className="txn-val">{invoice.razorpayOrderId}</span>
          </div>
          <div className="txn-row">
            <span className="txn-key">Amount</span>
            <span className="txn-val amount">₹{(invoice.amount / 100).toFixed(2)}</span>
          </div>
          <div className="txn-row">
            <span className="txn-key">Status</span>
            <span className="txn-val">{invoice.status}</span>
          </div>
          <div className="txn-row">
            <span className="txn-key">Name</span>
            <span className="txn-val">{form.name}</span>
          </div>
          <div className="txn-row">
            <span className="txn-key">Email</span>
            <span className="txn-val">{form.email}</span>
          </div>
        </div>

        {invoice.shortUrl && (
          <a className="invoice-link" href={invoice.shortUrl} target="_blank" rel="noopener noreferrer">
            🧾 View Invoice
          </a>
        )}

        {error && (
          <div className="error-banner">
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <button id="btn-pay-now" className="btn btn-primary" onClick={handlePayNow} disabled={loading}>
          {loading ? <><span className="spinner" />Opening…</> : <>🔒 Pay Now</>}
        </button>
        <button id="btn-edit-details" className="btn" onClick={handleEditDetails} disabled={loading}>
          ← Edit Details
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="card-title">Enter Payment Details</h2>
      <p className="card-subtitle">Fill in your information to generate invoice</p>
      <form className="form-grid" onSubmit={handleGenerateInvoice} id="payment-form">
        <div className="form-row">
          <div className="field">
            <label>Full Name</label>
            <input
              id="field-name"
              type="text"
              placeholder="Rafik Ahmed"
              value={form.name}
              onChange={set("name")}
              autoComplete="name"
              required
            />
          </div>
          <div className="field">
            <label>Email</label>
            <input
              id="field-email"
              type="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={set("email")}
              autoComplete="email"
              required
            />
          </div>
        </div>
        <div className="field">
          <label>Address</label>
          <textarea
            id="field-address"
            rows={2}
            placeholder="123 Street, City, State"
            value={form.address}
            onChange={set("address")}
          />
        </div>
        <div className="field">
          <label>Amount (INR)</label>
          <div className="amount-wrap">
            <span className="amount-prefix">₹</span>
            <input
              id="field-amount"
              type="number"
              min="1"
              step="0.01"
              placeholder="499.00"
              value={form.amount}
              onChange={set("amount")}
              required
            />
          </div>
        </div>
        {error && (
          <div className="error-banner">
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}
        <button id="btn-generate-invoice" className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? <><span className="spinner" />Generating…</> : <>🧾 Generate Invoice</>}
        </button>
      </form>
    </div>
  );
}
