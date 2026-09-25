// Shared helpers used by all pages under app/static/.

function parseGermanDate(str) {
  if (!str) return null;
  const parts = str.split(".").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return null;
  const [day, month, year] = parts;
  return new Date(year, month - 1, day);
}

function startOfToday() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

function toGermanDate(isoDate) {
  if (!isoDate) return null;
  const [y, m, d] = isoDate.split("-");
  return `${d}.${m}.${y}`;
}

function toISODate(date) {
  if (!date) return "";
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function formatEuro(value) {
  const formatted = value.toLocaleString("de-DE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${formatted} €`;
}

function docTypeLabel(doc) {
  if (doc.doc_type === "angebot") return "Angebot";
  if (doc.doc_type === "abschlagsrechnung") return `${doc.abschlag_number}. Abschlagsrechnung`;
  return "Rechnung";
}

function openModal(overlay) { overlay.classList.add("open"); }
function closeModal(overlay) { overlay.classList.remove("open"); }

function wireModal(openBtnId, closeBtnId, overlayId) {
  const overlay = document.getElementById(overlayId);
  document.getElementById(openBtnId).addEventListener("click", () => openModal(overlay));
  document.getElementById(closeBtnId).addEventListener("click", () => closeModal(overlay));
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeModal(overlay);
  });
  return overlay;
}

function wireSidebar(sidebarId, onChange) {
  document.getElementById(sidebarId).addEventListener("click", (e) => {
    const btn = e.target.closest(".beleg-sidebar-item");
    if (!btn) return;
    document
      .querySelectorAll(`#${sidebarId} .beleg-sidebar-item`)
      .forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    onChange(btn.dataset.filter);
  });
}

// --- App navigation bar ---
const NAV_ITEMS = [
  { label: "Dashboard", href: "/" },
  { label: "Belege", href: "/belege" },
  { label: "Finanzen", items: [{ label: "Firmendaten", href: "/finanzen" }] },
  { label: "Kontakte", href: "/kontakte" },
  { label: "Artikel", href: "/artikel" },
  {
    label: "Buchhaltung",
    items: [
      { label: "Baustellen", href: "/baustellen" },
      { label: "Rechnungen schreiben", href: "/rechnungen-schreiben" },
    ],
  },
  { label: "Lohn", href: "/lohn" },
  {
    label: "Ausbauplan (Beta)",
    items: [
      { label: "Angebote", href: "/ausbauplan#angebote" },
      { label: "Rechnungen", href: "/ausbauplan#rechnungen" },
      { label: "Baustellen", href: "/ausbauplan#baustellen" },
      { label: "Team", href: "/ausbauplan#team" },
    ],
  },
];

function renderNav(activePath) {
  const container = document.getElementById("appNav");
  if (!container) return;

  const inner = document.createElement("div");
  inner.className = "app-nav-inner";

  for (const item of NAV_ITEMS) {
    if (item.items) {
      const isActive = item.items.some(
        (sub) => sub.href === activePath || sub.href.split("#")[0] === activePath
      );
      const dropdown = document.createElement("div");
      dropdown.className = "app-nav-dropdown";
      dropdown.innerHTML = `
        <button type="button" class="app-nav-item app-nav-dropdown-toggle${isActive ? " active" : ""}">${item.label} ▾</button>
        <div class="app-nav-dropdown-menu">
          ${item.items.map((sub) => `<a href="${sub.href}">${sub.label}</a>`).join("")}
        </div>
      `;
      inner.appendChild(dropdown);
    } else {
      const a = document.createElement("a");
      a.className = "app-nav-item" + (item.href === activePath ? " active" : "");
      a.href = item.href;
      a.textContent = item.label;
      inner.appendChild(a);
    }
  }

  const nav = document.createElement("nav");
  nav.className = "app-nav";
  nav.appendChild(inner);
  container.replaceChildren(nav);

  document.querySelectorAll(".app-nav-dropdown-toggle").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const dropdown = btn.closest(".app-nav-dropdown");
      const wasOpen = dropdown.classList.contains("open");
      document.querySelectorAll(".app-nav-dropdown.open").forEach((d) => d.classList.remove("open"));
      if (!wasOpen) dropdown.classList.add("open");
    });
  });

  document.addEventListener("click", () => {
    document.querySelectorAll(".app-nav-dropdown.open").forEach((d) => d.classList.remove("open"));
  });
}
