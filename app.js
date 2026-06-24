"use strict";

const CATEGORY_ORDER = ["Anime", "Software", "AI", "Movies"];
const CATEGORY_ICON = { Anime: "🎏", Software: "🧰", AI: "🤖", Movies: "🎬" };

let DATA = null;
let activeCat = CATEGORY_ORDER[0];
let query = "";

const $ = (sel) => document.querySelector(sel);

async function load() {
  try {
    const res = await fetch("data/links.json", { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    DATA = await res.json();
  } catch (e) {
    $("#content").innerHTML =
      '<p class="empty">Could not load data/links.json — ' + e.message + "</p>";
    return;
  }
  // keep only categories that exist, in preferred order
  const present = CATEGORY_ORDER.filter((c) => DATA.categories[c]);
  if (present.length) activeCat = present[0];
  renderTabs(present);
  renderMeta();
  render();
  wireSearch();
}

function renderTabs(cats) {
  const tabs = $("#tabs");
  tabs.innerHTML = "";
  cats.forEach((cat) => {
    const el = document.createElement("button");
    el.className = "tab" + (cat === activeCat ? " active" : "");
    el.innerHTML =
      (CATEGORY_ICON[cat] || "") + " " + cat +
      '<span class="count">' + DATA.categories[cat].length + "</span>";
    el.onclick = () => {
      activeCat = cat;
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      el.classList.add("active");
      render();
      window.scrollTo({ top: 0, behavior: "smooth" });
    };
    tabs.appendChild(el);
  });
}

function renderMeta() {
  const total = Object.values(DATA.categories).reduce((a, b) => a + b.length, 0);
  let when = DATA.generated_at;
  try {
    when = new Date(DATA.generated_at).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch (e) {}
  $("#meta").textContent =
    total.toLocaleString() + " links · last updated " + when;
}

function matches(entry, q) {
  if (!q) return true;
  const hay = (entry.name + " " + entry.desc + " " + entry.section + " " + entry.url).toLowerCase();
  return q.split(/\s+/).every((term) => hay.includes(term));
}

function hostOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, ""); }
  catch (e) { return ""; }
}

function render() {
  const content = $("#content");
  const items = (DATA.categories[activeCat] || []).filter((e) => matches(e, query));

  if (!items.length) {
    content.innerHTML = '<p class="empty">No links match “' + escapeHtml(query) + '”.</p>';
    return;
  }

  // group by section
  const groups = {};
  for (const e of items) {
    const key = e.section || "Other";
    (groups[key] = groups[key] || []).push(e);
  }

  let html = "";
  for (const section of Object.keys(groups)) {
    html += '<h2 class="section-title">' + escapeHtml(section) +
            " · " + groups[section].length + "</h2>";
    html += '<div class="grid">';
    for (const e of groups[section]) {
      html += card(e);
    }
    html += "</div>";
  }
  content.innerHTML = html;
}

function card(e) {
  const host = hostOf(e.url);
  const mirrors = (e.mirrors || [])
    .map((m, i) => '<a href="' + escapeAttr(m) + '" target="_blank" rel="noopener">mirror ' + (i + 1) + "</a>")
    .join("");
  return (
    '<div class="card">' +
      '<a class="name" href="' + escapeAttr(e.url) + '" target="_blank" rel="noopener">' +
        escapeHtml(e.name) +
        (host ? ' <span class="ext">' + escapeHtml(host) + "</span>" : "") +
      "</a>" +
      (e.desc ? '<div class="desc">' + escapeHtml(e.desc) + "</div>" : "") +
      (mirrors ? '<div class="mirrors">' + mirrors + "</div>" : "") +
    "</div>"
  );
}

function wireSearch() {
  const input = $("#search");
  let t;
  input.addEventListener("input", () => {
    clearTimeout(t);
    t = setTimeout(() => {
      query = input.value.trim().toLowerCase();
      render();
    }, 120);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== input) {
      e.preventDefault();
      input.focus();
    }
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

load();
