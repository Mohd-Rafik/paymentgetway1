export default function SuccessScreen({ data, onReset }) {
  const rows = [
    { key: "Order ID",    val: data.orderId,                             cls: "" },
    { key: "Payment ID",  val: data.paymentId || "—",                    cls: "" },
    { key: "Amount Paid", val: `₹${parseFloat(data.amount).toFixed(2)}`, cls: "amount" },
    { key: "Method",      val: data.paymentMethod || "—",                cls: "method" },
    { key: "Customer",    val: data.name,                                cls: "" },
    { key: "Email",       val: data.email,                               cls: "" },
  ];

  return (
    <div className="card result-card">
      <div className="result-icon success">✅</div>
      <h2 className="result-title success">Payment Successful!</h2>
      <p className="result-msg">
        Your payment has been verified and recorded.<br />
        A confirmation will be sent to <strong>{data.email}</strong>.
      </p>
      <div className="txn-details">
        {rows.map(({ key, val, cls }) => (
          <div key={key} className="txn-row">
            <span className="txn-key">{key}</span>
            <span className={`txn-val ${cls}`}>{val}</span>
          </div>
        ))}
      </div>
      {data.invoiceUrl && (
        <a
          id="invoice-link"
          className="invoice-link"
          href={data.invoiceUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          🧾 View Invoice
        </a>
      )}
      <button id="btn-new-payment" className="btn btn-success" onClick={onReset}>
        ＋ New Payment
      </button>
    </div>
  );
}
