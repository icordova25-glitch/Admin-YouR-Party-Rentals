window.YPR_CONFIG = {
  bookingEndpoint: "",
  businessEmail: "bookings@yourrpartyrentals.com",
  businessPhone: "+15551234567",
  paymentCheckoutUrl: "",
  apiBaseUrl: "https://your-party-rentals-api.onrender.com",
};

const apiBaseUrl = window.YPR_CONFIG.apiBaseUrl.replace(/\/$/, "");
const nativeFetch = window.fetch.bind(window);
window.fetch = (input, init) => {
  if (typeof input === "string" && input.startsWith("/api/")) {
    return nativeFetch(`${apiBaseUrl}${input}`, init);
  }
  return nativeFetch(input, init);
};
