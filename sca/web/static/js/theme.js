/**
 * Theme toggle management with localStorage persistence.
 */

const STORAGE_KEY = "sca_theme";

export function initTheme() {
  let theme = "dark";
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") {
      theme = saved;
    }
  } catch (e) {
    // localStorage may be disabled
  }

  applyTheme(theme);

  const themeBtn = document.getElementById("btn-theme");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      applyTheme(next);
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch (e) {}
    });
  }
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const themeBtn = document.getElementById("btn-theme");
  if (themeBtn) {
    themeBtn.setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} theme`);
    const iconSpan = themeBtn.querySelector(".theme-icon");
    if (iconSpan) {
      iconSpan.textContent = theme === "dark" ? "☀️" : "🌙";
    }
  }
}
