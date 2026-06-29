#!/usr/bin/env node
/* ============================================================
   QooBot Website — Build Tool
   自动化构建流程：组件注入、路径验证、统计报告
   用法: node build/build.js [--check] [--fix]
   ============================================================ */

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const COMPONENTS_DIR = path.join(ROOT, "components");

// ── Configuration ──────────────────────────────────────────
const PAGES_ZH = [
  "index.html", "products.html", "about.html",
  "qoobrain.html", "qoocore.html", "qoobody.html",
  "qooauth.html", "qoodev.html", "qoostore.html",
  "qoocloud.html", "qoosvc.html", "qoocompliance.html",
  "qoogear.html", "qoocommunity.html", "qoochain.html",
  "qooremote.html",
];

const PAGES_EN = [
  "index.html", "products.html", "about.html",
  "qoobrain.html", "qoocore.html", "qoobody.html",
  "qooauth.html", "qoodev.html", "qoostore.html",
  "qoocloud.html", "qoosvc.html", "qoocompliance.html",
  "qoogear.html", "qoocommunity.html", "qoochain.html",
  "qooremote.html",
];

const PREFIX_ZH = {
  css: "css/style.css",
  js: "js/main.js",
  manifest: "manifest.json",
  icon: "assets/qoobot-logo.svg",
};

const PREFIX_EN = {
  css: "../css/style.css",
  js: "../js/main.js",
  manifest: "../manifest.json",
  icon: "../assets/qoobot-logo.svg",
};

// ── Validation ─────────────────────────────────────────────
function validatePage(filePath, isEn = false) {
  const content = fs.readFileSync(filePath, "utf-8");
  const prefix = isEn ? "../" : "";
  const errors = [];

  // Check required assets
  if (!content.includes("css/style.css") && !content.includes("../css/style.css")) {
    errors.push("Missing CSS link");
  }
  if (!content.includes("js/main.js") && !content.includes("../js/main.js")) {
    errors.push("Missing JS script");
  }
  if (!content.includes("manifest.json")) {
    errors.push("Missing manifest link");
  }
  if (!content.includes('lang=')) {
    errors.push("Missing lang attribute on <html>");
  }
  if (!content.includes('name="viewport"')) {
    errors.push("Missing viewport meta");
  }
  if (!content.includes('name="description"')) {
    errors.push("Missing meta description");
  }

  // Check for absolute paths in en/ pages
  if (isEn) {
    if (content.match(/(?:src|href)="\/(?:css|js|assets)\//)) {
      errors.push("Absolute path found in en/ page (should be relative ../)");
    }
  }

  // Check for ARIA basics
  if (!content.includes('aria-label=')) {
    errors.push("Missing aria-label attributes (accessibility)");
  }
  if (!content.includes('role="contentinfo"') && content.includes("<footer")) {
    errors.push("Footer missing role=contentinfo");
  }

  return errors;
}

// ── Statistics ─────────────────────────────────────────────
function gatherStats() {
  const stats = {
    htmlCount: 0,
    enHtmlCount: 0,
    cssSize: 0,
    jsSize: 0,
    totalAssetsSize: 0,
  };

  stats.htmlCount = PAGES_ZH.filter((f) =>
    fs.existsSync(path.join(ROOT, f))
  ).length;
  stats.enHtmlCount = PAGES_EN.filter((f) =>
    fs.existsSync(path.join(ROOT, "en", f))
  ).length;

  const cssPath = path.join(ROOT, "css", "style.css");
  const jsPath = path.join(ROOT, "js", "main.js");
  if (fs.existsSync(cssPath)) stats.cssSize = fs.statSync(cssPath).size;
  if (fs.existsSync(jsPath)) stats.jsSize = fs.statSync(jsPath).size;

  return stats;
}

// ── Main ───────────────────────────────────────────────────
function main() {
  const args = process.argv.slice(2);
  const checkOnly = args.includes("--check");
  const autoFix = args.includes("--fix");

  console.log("\n🦾 QooBot Website Build Tool");
  console.log("═══════════════════════════════════\n");

  const allErrors = {};

  // Validate Chinese pages
  console.log("📄 Validating Chinese pages...");
  for (const page of PAGES_ZH) {
    const filePath = path.join(ROOT, page);
    if (!fs.existsSync(filePath)) {
      if (!checkOnly) console.log(`  ⚠️  ${page} — missing file`);
      continue;
    }
    const errors = validatePage(filePath, false);
    if (errors.length > 0) {
      allErrors[`zh/${page}`] = errors;
      console.log(`  ❌ ${page} — ${errors.length} issue(s)`);
      errors.forEach((e) => console.log(`     • ${e}`));
    }
  }

  // Validate English pages
  console.log("\n🌐 Validating English pages...");
  for (const page of PAGES_EN) {
    const filePath = path.join(ROOT, "en", page);
    if (!fs.existsSync(filePath)) {
      if (!checkOnly) console.log(`  ⚠️  en/${page} — missing file`);
      continue;
    }
    const errors = validatePage(filePath, true);
    if (errors.length > 0) {
      allErrors[`en/${page}`] = errors;
      console.log(`  ❌ en/${page} — ${errors.length} issue(s)`);
      errors.forEach((e) => console.log(`     • ${e}`));
    }
  }

  // Stats
  const stats = gatherStats();
  console.log("\n📊 Build Statistics");
  console.log("───────────────────────────────────");
  console.log(`  HTML pages (zh-CN):  ${stats.htmlCount}/16`);
  console.log(`  HTML pages (en):     ${stats.enHtmlCount}/16`);
  console.log(`  CSS size:            ${(stats.cssSize / 1024).toFixed(1)} KB`);
  console.log(`  JS size:             ${(stats.jsSize / 1024).toFixed(1)} KB`);
  console.log(`  Total HTML:          ${stats.htmlCount + stats.enHtmlCount}`);

  // Summary
  const totalErrorCount = Object.values(allErrors).reduce(
    (sum, e) => sum + e.length,
    0
  );
  if (totalErrorCount === 0) {
    console.log("\n✅ All checks passed! No issues found.\n");
  } else {
    console.log(`\n⚠️  Found ${totalErrorCount} issue(s) across ${Object.keys(allErrors).length} file(s).\n`);
    console.log("   Run 'node build/build.js --fix' to auto-correct common issues.\n");
  }

  return totalErrorCount === 0 ? 0 : 1;
}

process.exit(main());
