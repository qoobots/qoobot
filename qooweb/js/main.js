/* ============================================================
   QooBot Website — Minimal JS
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initMobileNav();
  initScrollReveal();
  initProgressBars();
});

/* --- Theme Toggle --- */
function initTheme() {
  const toggle = document.getElementById("theme-toggle");
  if (!toggle) return;

  // Check saved preference or system
  const saved = localStorage.getItem("qoobot-theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const isDark = saved === "dark" || (!saved && prefersDark);

  applyTheme(isDark);

  toggle.addEventListener("click", () => {
    const current = document.documentElement.hasAttribute("data-theme");
    applyTheme(!current);
  });

  // Update icon
  updateThemeIcon(isDark);
}

function applyTheme(dark) {
  if (dark) {
    document.documentElement.setAttribute("data-theme", "dark");
    localStorage.setItem("qoobot-theme", "dark");
  } else {
    document.documentElement.removeAttribute("data-theme");
    localStorage.setItem("qoobot-theme", "light");
  }
  updateThemeIcon(dark);
}

function updateThemeIcon(dark) {
  const toggle = document.getElementById("theme-toggle");
  if (!toggle) return;
  toggle.textContent = dark ? "☀️" : "🌙";
  toggle.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
}

/* --- Mobile Nav --- */
function initMobileNav() {
  const toggle = document.getElementById("nav-toggle");
  const links = document.getElementById("nav-links");
  if (!toggle || !links) return;

  toggle.addEventListener("click", () => {
    links.classList.toggle("open");
  });

  // Close nav on link click
  links.querySelectorAll("a").forEach((a) => {
    a.addEventListener("click", () => links.classList.remove("open"));
  });

  // Close nav on outside click
  document.addEventListener("click", (e) => {
    if (!toggle.contains(e.target) && !links.contains(e.target)) {
      links.classList.remove("open");
    }
  });
}

/* --- Scroll Reveal --- */
function initScrollReveal() {
  const elements = document.querySelectorAll(".fade-up");

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
  );

  elements.forEach((el) => observer.observe(el));
}

/* --- Progress Bar Animation --- */
function initProgressBars() {
  const bars = document.querySelectorAll(".progress-bar-fill");

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const targetWidth = entry.target.style.width || entry.target.getAttribute("data-width") || "0%";
          entry.target.style.width = targetWidth;
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.3 }
  );

  bars.forEach((bar) => {
    const w = bar.style.width;
    bar.style.width = "0%";
    bar.setAttribute("data-width", w);
    observer.observe(bar);
  });
}
