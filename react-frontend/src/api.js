const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let json;
  try {
    json = await res.json();
  } catch {
    json = {};
  }

  if (!res.ok) {
    const msg = json?.detail || json?.message || `Request failed (${res.status})`;
    throw new Error(msg);
  }

  return json;
}

export async function createInvoice({ name, email, address, amount }) {
  const res = await request("/api/payment/create-invoice", {
    method: "POST",
    body: JSON.stringify({ name, email, address, amount }),
  });
  return res.data; 
}

export async function verifyPayment({ razorpay_order_id, razorpay_payment_id, razorpay_signature }) {
  const res = await request("/api/payment/verify-payment", {
    method: "POST",
    body: JSON.stringify({ razorpay_order_id, razorpay_payment_id, razorpay_signature }),
  });
  return res.data; 
}


export async function markPaymentFailed(razorpay_order_id, reason) {
  return request("/api/payment/payment-failed", {
    method: "POST",
    body: JSON.stringify({ razorpay_order_id, reason }),
  });
}

export async function getTransaction(orderId) {
  return request(`/api/payment/transaction/${orderId}`, { method: "GET" });
}