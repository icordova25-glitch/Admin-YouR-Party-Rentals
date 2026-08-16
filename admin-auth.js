(() => {
  const key = "yourr_party_rentals_gallery_admin_auth";
  const panel = document.getElementById("admin-panel");
  const login = document.getElementById("admin-login");
  const loginForm = document.getElementById("admin-login-form");
  const authHeader = () => {
    const credentials = JSON.parse(sessionStorage.getItem(key) || "null");
    return credentials ? { Authorization: `Basic ${btoa(`${credentials.username}:${credentials.password}`)}` } : {};
  };
  const mount = () => {
    if (!panel || document.getElementById("change-credentials-form")) return;
    const form = document.createElement("form");
    form.id = "change-credentials-form";
    form.className = "booking-form";
    form.innerHTML = `<h3>Admin Login Credentials</h3><p>Temporary login: admin / yourr-admin. Change it after signing in.</p><label>New Username<input name="username" minlength="3" required autocomplete="username"></label><label>New Password<input type="password" name="password" minlength="8" required autocomplete="new-password"></label><label>Confirm New Password<input type="password" name="confirmPassword" minlength="8" required autocomplete="new-password"></label><button class="submit-btn" type="submit">Change Login Credentials</button><p id="credentials-status"></p>`;
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const password = String(data.get("password") || "");
      const status = document.getElementById("credentials-status");
      if (password !== String(data.get("confirmPassword") || "")) { status.textContent = "Passwords do not match."; return; }
      const response = await fetch("/api/admin/auth", { method: "PUT", headers: { "Content-Type": "application/json", ...authHeader() }, body: JSON.stringify({ username: String(data.get("username") || "").trim(), password }) });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) { status.textContent = body.error || "Could not change credentials."; return; }
      sessionStorage.removeItem(key);
      panel.hidden = true;
      login.hidden = false;
      document.getElementById("login-status").textContent = "Credentials changed. Log in again with the new credentials.";
    });
    panel.querySelector(".admin-settings")?.appendChild(form);
  };
  const observer = new MutationObserver(mount);
  observer.observe(panel, { attributes: true });
  mount();
  loginForm?.addEventListener("submit", () => setTimeout(mount, 250));
})();
