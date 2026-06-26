/* ============================================================
   QooBot Website — Minimal JS
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initMobileNav();
  initScrollReveal();
  initHeroParticles();
});

/* --- Theme Toggle --- */
function initTheme() {
  const toggle = document.getElementById("theme-toggle");
  if (!toggle) return;

  // Check saved preference, default to dark
  const saved = localStorage.getItem("qoobot-theme");
  const isDark = saved !== "light";

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

/* --- Hero Particles --- */
function initHeroParticles() {
  const canvas = document.getElementById("hero-particles");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const hero = canvas.closest(".hero");
  if (!hero) return;

  let particles = [];
  let mouse = { x: -9999, y: -9999 };
  let width, height;

  const PARTICLE_COUNT = 70;
  const CONNECTION_DIST = 140;
  const MOUSE_RADIUS = 180;
  const COLORS = [
    "rgba(41, 151, 255, 0.7)",
    "rgba(64, 169, 255, 0.65)",
    "rgba(145, 202, 255, 0.55)",
    "rgba(175, 82, 222, 0.55)",
    "rgba(191, 90, 242, 0.5)",
    "rgba(0, 113, 227, 0.6)",
  ];

  function resize() {
    const rect = hero.getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    canvas.width = width * devicePixelRatio;
    canvas.height = height * devicePixelRatio;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  }

  class Particle {
    constructor() {
      this.reset();
      this.y = Math.random() * (height || window.innerHeight);
      this.opacity = Math.random() * 0.5 + 0.2;
    }

    reset() {
      this.x = Math.random() * (width || window.innerWidth);
      this.y = Math.random() * (height || window.innerHeight);
      this.vx = (Math.random() - 0.5) * 0.6;
      this.vy = (Math.random() - 0.5) * 0.6;
      this.radius = Math.random() * 2.5 + 1;
      this.color = COLORS[Math.floor(Math.random() * COLORS.length)];
      this.baseOpacity = Math.random() * 0.5 + 0.2;
      this.opacity = this.baseOpacity;
    }

    update() {
      this.vx += (Math.random() - 0.5) * 0.02;
      this.vy += (Math.random() - 0.5) * 0.02;
      this.vx *= 0.999;
      this.vy *= 0.999;
      this.x += this.vx;
      this.y += this.vy;

      // Mouse interaction
      const dx = this.x - mouse.x;
      const dy = this.y - mouse.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < MOUSE_RADIUS && dist > 0) {
        const force = (MOUSE_RADIUS - dist) / MOUSE_RADIUS;
        this.vx += (dx / dist) * force * 0.5;
        this.vy += (dy / dist) * force * 0.5;
        this.opacity = Math.min(1, this.baseOpacity + force * 0.4);
      } else {
        this.opacity = this.baseOpacity;
      }

      // Wrap edges
      if (this.x < -20) this.x = width + 20;
      if (this.x > width + 20) this.x = -20;
      if (this.y < -20) this.y = height + 20;
      if (this.y > height + 20) this.y = -20;
    }

    draw(ctx) {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
      ctx.fillStyle = this.color.replace(/[\d.]+\)$/, this.opacity + ")");
      ctx.fill();

      // Glow halo
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.radius * 2.5, 0, Math.PI * 2);
      ctx.fillStyle = this.color.replace(/[\d.]+\)$/, (this.opacity * 0.15) + ")");
      ctx.fill();
    }
  }

  function initParticles() {
    particles = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push(new Particle());
    }
  }

  function drawConnections() {
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < CONNECTION_DIST) {
          const opacity = (1 - dist / CONNECTION_DIST) * 0.15;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = "rgba(41, 151, 255, " + opacity + ")";
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }
    }
  }

  function animate() {
    ctx.clearRect(0, 0, width, height);
    particles.forEach(p => p.update());
    drawConnections();
    particles.forEach(p => p.draw(ctx));
    requestAnimationFrame(animate);
  }

  resize();
  initParticles();

  hero.addEventListener("mousemove", (e) => {
    const rect = hero.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
  });

  hero.addEventListener("mouseleave", () => {
    mouse.x = -9999;
    mouse.y = -9999;
  });

  window.addEventListener("resize", () => {
    resize();
    particles.forEach(p => {
      p.x = Math.min(p.x, width);
      p.y = Math.min(p.y, height);
    });
  });

  animate();
}
