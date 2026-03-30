/**
 * RS Supplement Deals - Dashboard Frontend
 *
 * Handles: data loading from embedded JSON, product card rendering,
 * filtering, sorting, search, category tabs, stats bar,
 * mobile filter drawer, and lazy loading.
 */

// ---- Category Normalization Map ----
const CATEGORY_MAP = {
  proteini: "Proteini",
  "whey protein": "Proteini",
  "vegan protein": "Proteini",
  kazein: "Proteini",
  "protein bar": "Proteini",
  gaineri: "Proteini",
  gejneri: "Proteini",
  kreatin: "Kreatin",
  kreatini: "Kreatin",
  "kreatin monohidrat": "Kreatin",
  "amino kiseline": "Amino kiseline",
  aminokiseline: "Amino kiseline",
  "aminokiseline u prahu": "Amino kiseline",
  bcaa: "Amino kiseline",
  glutamin: "Amino kiseline",
  citrulin: "Amino kiseline",
  vitamini: "Vitamini i minerali",
  minerali: "Vitamini i minerali",
  magnezijum: "Vitamini i minerali",
  cink: "Vitamini i minerali",
  kalcijum: "Vitamini i minerali",
  kalijum: "Vitamini i minerali",
  gvožđe: "Vitamini i minerali",
  hrom: "Vitamini i minerali",
  selen: "Vitamini i minerali",
  "kompleksi minerala": "Vitamini i minerali",
  spirulina: "Vitamini i minerali",
  probiotici: "Zdravlje",
  kolagen: "Zdravlje",
  "hijaluronska kiselina": "Zdravlje",
  "koenzim q10": "Zdravlje",
  "omega masne kiseline": "Zdravlje",
  ašvaganda: "Zdravlje",
  kurkumin: "Zdravlje",
  maka: "Zdravlje",
  tribulus: "Zdravlje",
  melatonin: "Zdravlje",
  "zastita zglobova tetiva i ligamenata": "Zdravlje",
  "korisne masti i biljni ekstrakti": "Zdravlje",
  mršavljenje: "Mršavljenje",
  "sagorevaci masti": "Mršavljenje",
  "l-karnitin": "Mršavljenje",
  "l carnitine": "Mršavljenje",
  "pre workout": "Pre-Workout",
  "no reaktori": "Pre-Workout",
  "zdrava hrana": "Zdrava hrana",
  "cokoladice i napici": "Zdrava hrana",
  akcije: "Ostalo",
  akcija: "Ostalo",
  rasprodaja: "Ostalo",
  suplementi: "Ostalo",
  ostalo: "Ostalo",
  biotech: "Ostalo",
  ostrovit: "Ostalo",
  nutriversum: "Ostalo",
  blastex: "Ostalo",
  "amix nutrition": "Ostalo",
  "5 stars": "Ostalo",
  "applied nutrition": "Ostalo",
  "6pak nutrition": "Ostalo",
  "extrifit sports nutrition": "Ostalo",
  vitalikum: "Ostalo",
};

// ---- Non-supplement filter lists ----
const NON_SUPPLEMENT_CATS = [
  "fitnes oprema",
  "sejkeri",
  "rukavice za trening",
  "pojas za teretanu",
  "majice",
  "sportska oprema",
];
const NON_SUPPLEMENT_KEYWORDS = [
  "torba",
  "torbica",
  "šejker",
  "shaker",
  "rukavice",
  "pojas za",
  "majica",
  "čarape",
  "patike",
  "držač za",
  "noževi",
  "weighted vest",
  "gym bag",
];

// ---- Store Color Dot Map (brand guidelines) ----
const STORE_COLORS = {
  "GymBeam": "#ff6b00",
  "Supplement Store": "#2563eb",
  "FitLab": "#7c3aed",
  "Proteini.si": "#059669",
  "TitaniumSport": "#64748b",
  "Dobrobit": "#d97706",
  "ExYu Fitness": "#dc2626",
  "LAMA": "#0891b2",
  "AMG Sport": "#be123c",
  "Ogistra Nutrition": "#9333ea",
  "SuperProtein": "#0284c7",
  "Superior14": "#4f46e5",
  "ATP Sport": "#15803d",
  "Spartan Shop": "#b45309",
  "X Sport": "#374151",
};

// ---- Category Color Map ----
const CATEGORY_COLORS = {
  Proteini: "bg-blue-50 text-blue-700",
  Kreatin: "bg-purple-50 text-purple-700",
  "Amino kiseline": "bg-orange-50 text-orange-700",
  "Vitamini i minerali": "bg-green-50 text-green-700",
  Zdravlje: "bg-teal-50 text-teal-700",
  Mršavljenje: "bg-pink-50 text-pink-700",
  "Pre-Workout": "bg-red-50 text-red-700",
  "Zdrava hrana": "bg-amber-50 text-amber-700",
  Ostalo: "bg-slate-100 text-slate-500",
};

// ---- State ----
let allProducts = [];
let filteredProducts = [];
let weeklySummary = {};
let storeData = {};
let currentViewMode = "discounts";
let displayedCount = 0;
const BATCH_SIZE = 60;

// Active filters
let activeStores = new Set();
let activeCategory = "";
let minDiscount = 0;
let searchQuery = "";
let currentSort = "discount_desc";
let activeCategoryTab = "";

// ---- Initialization ----
document.addEventListener("DOMContentLoaded", () => {
  loadData();
  setupMobileDrawer();
});

// ---- Data Loading (PRESERVED - reads from #supplementsData) ----
function loadData() {
  const dataEl = document.getElementById("supplementsData");
  if (!dataEl) {
    showError("Nema podataka za prikaz.");
    return;
  }

  let raw = dataEl.textContent.trim();
  if (!raw || raw === "/* __SUPPLEMENT_DATA_PLACEHOLDER__ */") {
    showError(
      "Dashboard jos nije generisan. Pokrenite: python supplement_scraper.py",
    );
    return;
  }

  try {
    storeData = JSON.parse(raw);
  } catch (e) {
    showError("Greska pri ucitavanju podataka: " + e.message);
    return;
  }

  allProducts = storeData.products || [];
  weeklySummary = storeData.weekly_summary || {};

  // Filter out out-of-stock products
  allProducts = allProducts.filter((p) => p.in_stock !== false);

  // Filter out non-supplement products
  allProducts = allProducts.filter((p) => {
    const catLower = (p.category || "").toLowerCase();
    if (NON_SUPPLEMENT_CATS.some((c) => catLower.includes(c))) return false;
    const nameLower = (p.name || "").toLowerCase();
    if (NON_SUPPLEMENT_KEYWORDS.some((kw) => nameLower.includes(kw)))
      return false;
    return true;
  });

  // Normalize categories (68 raw → ~10 clean)
  allProducts.forEach((p) => {
    const rawCat = (p.category || "").toLowerCase().trim();
    p.category = CATEGORY_MAP[rawCat] || "Ostalo";
  });

  // Update last-updated timestamp
  if (storeData.scraped_at) {
    const date = new Date(storeData.scraped_at);
    document.getElementById("lastUpdated").textContent =
      "Azurirano: " + formatDate(date);
  }

  // Empty state
  if (allProducts.length === 0) {
    const grid = document.getElementById("productGrid");
    grid.innerHTML = `
            <div class="col-span-full text-center py-16">
                <ph-package class="text-5xl text-slate-300 mx-auto mb-4"></ph-package>
                <h2 class="text-lg font-semibold text-slate-700 mb-2">Dashboard se ucitava...</h2>
                <p class="text-slate-500 text-sm">Podaci se prikupljaju sa srpskih online prodavnica suplemenata.</p>
                <p class="text-slate-400 text-xs mt-1">Dashboard se automatski azurira svakih 6 sati.</p>
                ${
                  storeData.stores_failed && storeData.stores_failed.length > 0
                    ? '<p class="text-red-500 text-xs mt-3">Neke prodavnice trenutno nisu dostupne. Sledece azuriranje ce pokusati ponovo.</p>'
                    : ""
                }
            </div>`;
    return;
  }

  // Build UI
  buildStoreFilters();
  buildCategoryFilter();
  buildCategoryTabs();
  populateStats();
  populateFooter();
  setupEventListeners();

  // Initial render
  applyFiltersAndRender();
}

// ---- Stats Bar ----
function populateStats() {
  const stores = storeData.stores_scraped || [];
  const totalProducts = allProducts.length;
  const discounted = allProducts.filter((p) => (p.discount_percent || 0) > 0);
  const onSaleCount = discounted.length;
  const avgDiscount =
    onSaleCount > 0
      ? Math.round(
          discounted.reduce((sum, p) => sum + (p.discount_percent || 0), 0) /
            onSaleCount,
        )
      : 0;

  // Header compact stats
  document.getElementById("headerProductCount").textContent = totalProducts;
  document.getElementById("headerSaleCount").textContent = onSaleCount;

  // Animate stat counters
  animateCount("statStores", stores.length);
  animateCount("statProducts", totalProducts);
  animateCount("statOnSale", onSaleCount);
  animateCount("statAvgDiscount", avgDiscount);
}

function animateCount(elementId, target) {
  const el = document.getElementById(elementId);
  if (!el || target === 0) {
    if (el) el.textContent = "0";
    return;
  }

  const duration = 1200;
  const startTime = performance.now();
  const easeOutQuart = (t) => 1 - Math.pow(1 - t, 4);

  function update(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = easeOutQuart(progress);
    el.textContent = Math.round(eased * target);

    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      el.textContent = target;
    }
  }

  requestAnimationFrame(update);
}

// ---- Category Tabs ----
function buildCategoryTabs() {
  const container = document.getElementById("categoryTabs");
  const categories = [
    ...new Set(allProducts.map((p) => p.category).filter(Boolean)),
  ].sort();

  // Count per category (only discounted in discount view)
  function getCatCount(cat) {
    if (!cat)
      return allProducts.filter((p) =>
        currentViewMode === "discounts" ? (p.discount_percent || 0) > 0 : true,
      ).length;
    return allProducts.filter(
      (p) =>
        p.category === cat &&
        (currentViewMode === "discounts"
          ? (p.discount_percent || 0) > 0
          : true),
    ).length;
  }

  const allCount = getCatCount(null);

  let html = `<button class="category-tab whitespace-nowrap px-4 py-2.5 min-h-[44px] text-sm font-medium transition-colors border-b-2 ${
    activeCategoryTab === ""
      ? "border-[#059669] text-[#059669] font-semibold"
      : "border-transparent text-[#999] hover:text-[#059669]"
  }" data-category="">Sve (${allCount})</button>`;

  categories.forEach((cat) => {
    const count = getCatCount(cat);
    if (count === 0) return;
    const isActive = activeCategoryTab === cat;
    html += `<button class="category-tab whitespace-nowrap px-4 py-2.5 min-h-[44px] text-sm font-medium transition-colors border-b-2 ${
      isActive
        ? "border-[#059669] text-[#059669] font-semibold"
        : "border-transparent text-[#999] hover:text-[#059669]"
    }" data-category="${escapeHtml(cat)}">${escapeHtml(cat)} (${count})</button>`;
  });

  container.innerHTML = html;

  // Event delegation for category tabs
  container.querySelectorAll(".category-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeCategoryTab = btn.dataset.category;
      // Also sync with category dropdown
      activeCategory = activeCategoryTab;
      document.getElementById("categoryFilter").value = activeCategoryTab;
      document.getElementById("mobileCategoryFilter").value = activeCategoryTab;
      applyFiltersAndRender();
      buildCategoryTabs(); // Refresh active state
    });
  });
}

// ---- Store Filters (checkbox-style for sidebar) ----
function buildStoreFilters() {
  const stores = [...new Set(allProducts.map((p) => p.store))].sort();
  activeStores = new Set(stores);

  const desktopContainer = document.getElementById("storeFilters");
  const mobileContainer = document.getElementById("mobileStoreFilters");

  function buildCheckboxes(container, prefix) {
    container.innerHTML = stores
      .map((store) => {
        const count = allProducts.filter((p) => p.store === store).length;
        const id = prefix + "-" + store.replace(/\s+/g, "-").toLowerCase();
        return `
                <label for="${id}" class="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors group">
                    <input type="checkbox" id="${id}" data-store="${escapeHtml(store)}" checked
                        class="w-4 h-4 rounded border-slate-300 text-[#606060] focus:ring-[#606060] cursor-pointer shrink-0">
                    <span class="text-sm text-slate-700 group-hover:text-slate-900 truncate flex-1">${escapeHtml(store)}</span>
                    <span class="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded-full shrink-0">${count}</span>
                </label>`;
      })
      .join("");

    // Wire up checkboxes
    container.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
      cb.addEventListener("change", () => {
        const store = cb.dataset.store;
        if (cb.checked) {
          activeStores.add(store);
        } else {
          activeStores.delete(store);
        }
        // Sync desktop & mobile
        syncStoreCheckboxes(store, cb.checked);
        applyFiltersAndRender();
      });
    });
  }

  buildCheckboxes(desktopContainer, "desktop");
  buildCheckboxes(mobileContainer, "mobile");
}

function syncStoreCheckboxes(store, checked) {
  document.querySelectorAll(`input[data-store="${store}"]`).forEach((cb) => {
    cb.checked = checked;
  });
}

// ---- Category Dropdown ----
function buildCategoryFilter() {
  const categories = [
    ...new Set(allProducts.map((p) => p.category).filter(Boolean)),
  ].sort();

  const optionsHtml =
    '<option value="">Sve kategorije</option>' +
    categories
      .map(
        (cat) =>
          `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`,
      )
      .join("");

  document.getElementById("categoryFilter").innerHTML = optionsHtml;
  document.getElementById("mobileCategoryFilter").innerHTML = optionsHtml;
}

// ---- Footer ----
function populateFooter() {
  const stores = storeData.stores_scraped || [];
  document.getElementById("footerStoreCount").textContent = stores.length;

  const footerLinks = document.getElementById("footerStoreLinks");
  footerLinks.innerHTML = stores
    .map(
      (store) =>
        `<div class="flex items-center gap-1.5 text-sm text-[#606060] hover:text-[#333] transition-colors">
            <ph-storefront class="text-xs shrink-0"></ph-storefront>
            <span class="truncate">${escapeHtml(store)}</span>
        </div>`,
    )
    .join("");
}

// ---- Event Listeners ----
function setupEventListeners() {
  // Search (debounced)
  const searchInput = document.getElementById("searchInput");
  let searchTimeout;
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      searchQuery = searchInput.value.trim().toLowerCase();
      applyFiltersAndRender();
    }, 250);
  });

  // Category dropdown (desktop)
  document.getElementById("categoryFilter").addEventListener("change", (e) => {
    activeCategory = e.target.value;
    activeCategoryTab = e.target.value;
    document.getElementById("mobileCategoryFilter").value = e.target.value;
    buildCategoryTabs();
    applyFiltersAndRender();
  });

  // Category dropdown (mobile)
  document
    .getElementById("mobileCategoryFilter")
    .addEventListener("change", (e) => {
      activeCategory = e.target.value;
      activeCategoryTab = e.target.value;
      document.getElementById("categoryFilter").value = e.target.value;
      buildCategoryTabs();
      applyFiltersAndRender();
    });

  // Discount range (desktop)
  const discountRange = document.getElementById("discountRange");
  discountRange.addEventListener("input", (e) => {
    minDiscount = parseInt(e.target.value, 10);
    document.getElementById("discountRangeValue").textContent =
      minDiscount + "%";
    document.getElementById("mobileDiscountRange").value = minDiscount;
    document.getElementById("mobileDiscountRangeValue").textContent =
      minDiscount + "%";
    applyFiltersAndRender();
  });

  // Discount range (mobile)
  const mobileDiscountRange = document.getElementById("mobileDiscountRange");
  mobileDiscountRange.addEventListener("input", (e) => {
    minDiscount = parseInt(e.target.value, 10);
    document.getElementById("mobileDiscountRangeValue").textContent =
      minDiscount + "%";
    document.getElementById("discountRange").value = minDiscount;
    document.getElementById("discountRangeValue").textContent =
      minDiscount + "%";
    applyFiltersAndRender();
  });

  // Sort (desktop)
  document.getElementById("sortSelect").addEventListener("change", (e) => {
    currentSort = e.target.value;
    document.getElementById("mobileSortSelect").value = e.target.value;
    applyFiltersAndRender();
  });

  // Sort (mobile)
  document
    .getElementById("mobileSortSelect")
    .addEventListener("change", (e) => {
      currentSort = e.target.value;
      document.getElementById("sortSelect").value = e.target.value;
      applyFiltersAndRender();
    });

  // View mode buttons (desktop)
  document
    .getElementById("btnDiscountsOnly")
    .addEventListener("click", () => setViewMode("discounts"));
  document
    .getElementById("btnAllProducts")
    .addEventListener("click", () => setViewMode("all"));

  // View mode buttons (mobile)
  document
    .getElementById("mBtnDiscountsOnly")
    .addEventListener("click", () => setViewMode("discounts"));
  document
    .getElementById("mBtnAllProducts")
    .addEventListener("click", () => setViewMode("all"));

  // Clear filters
  document
    .getElementById("clearFiltersBtn")
    .addEventListener("click", clearAllFilters);
  document
    .getElementById("mobileFilterClear")
    .addEventListener("click", clearAllFilters);
}

// ---- View Mode ----
function setViewMode(mode) {
  currentViewMode = mode;
  const isDiscounts = mode === "discounts";

  // Desktop buttons
  const btnD = document.getElementById("btnDiscountsOnly");
  const btnA = document.getElementById("btnAllProducts");
  btnD.className = `flex-1 py-2 text-xs font-semibold transition-colors ${isDiscounts ? "bg-[#059669] text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`;
  btnA.className = `flex-1 py-2 text-xs font-semibold transition-colors ${!isDiscounts ? "bg-[#059669] text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`;

  // Mobile buttons
  const mBtnD = document.getElementById("mBtnDiscountsOnly");
  const mBtnA = document.getElementById("mBtnAllProducts");
  mBtnD.className = `flex-1 py-2.5 text-sm font-semibold transition-colors ${isDiscounts ? "bg-[#059669] text-white" : "bg-white text-slate-600"}`;
  mBtnA.className = `flex-1 py-2.5 text-sm font-semibold transition-colors ${!isDiscounts ? "bg-[#059669] text-white" : "bg-white text-slate-600"}`;

  buildCategoryTabs();
  applyFiltersAndRender();
}

// ---- Clear Filters ----
function clearAllFilters() {
  // Reset state
  const stores = [...new Set(allProducts.map((p) => p.store))];
  activeStores = new Set(stores);
  activeCategory = "";
  activeCategoryTab = "";
  minDiscount = 0;
  searchQuery = "";
  currentSort = "discount_desc";
  currentViewMode = "discounts";

  // Reset UI elements
  document.getElementById("searchInput").value = "";
  document.getElementById("categoryFilter").value = "";
  document.getElementById("mobileCategoryFilter").value = "";
  document.getElementById("discountRange").value = 0;
  document.getElementById("mobileDiscountRange").value = 0;
  document.getElementById("discountRangeValue").textContent = "0%";
  document.getElementById("mobileDiscountRangeValue").textContent = "0%";
  document.getElementById("sortSelect").value = "discount_desc";
  document.getElementById("mobileSortSelect").value = "discount_desc";

  // Reset store checkboxes
  document
    .querySelectorAll(
      '#storeFilters input[type="checkbox"], #mobileStoreFilters input[type="checkbox"]',
    )
    .forEach((cb) => {
      cb.checked = true;
    });

  // Reset view mode
  setViewMode("discounts");

  // Rebuild tabs
  buildCategoryTabs();

  // Hide clear button
  document.getElementById("clearFiltersBtn").classList.add("hidden");

  applyFiltersAndRender();
}

// ---- Mobile Filter Drawer ----
function setupMobileDrawer() {
  const fab = document.getElementById("mobileFilterFab");
  const backdrop = document.getElementById("mobileFilterBackdrop");
  const drawer = document.getElementById("mobileFilterDrawer");
  const closeBtn = document.getElementById("mobileFilterClose");
  const applyBtn = document.getElementById("mobileFilterApply");

  function openDrawer() {
    backdrop.classList.remove("hidden");
    requestAnimationFrame(() => {
      backdrop.classList.remove("opacity-0");
      backdrop.classList.add("opacity-100");
      drawer.classList.remove("translate-x-full");
      drawer.classList.add("translate-x-0");
    });
    document.body.style.overflow = "hidden";
  }

  function closeDrawer() {
    backdrop.classList.remove("opacity-100");
    backdrop.classList.add("opacity-0");
    drawer.classList.remove("translate-x-0");
    drawer.classList.add("translate-x-full");
    document.body.style.overflow = "";
    setTimeout(() => backdrop.classList.add("hidden"), 300);
  }

  fab.addEventListener("click", openDrawer);
  closeBtn.addEventListener("click", closeDrawer);
  backdrop.addEventListener("click", closeDrawer);

  // Wire up mobile bottom nav filter button
  const mobileNavFilterBtn = document.getElementById("mobileNavFilter");
  if (mobileNavFilterBtn) {
    mobileNavFilterBtn.addEventListener("click", openDrawer);
  }
  applyBtn.addEventListener("click", () => {
    applyFiltersAndRender();
    closeDrawer();
  });
}

// ---- Filter + Sort + Render Pipeline ----
function applyFiltersAndRender() {
  // Filter
  filteredProducts = allProducts.filter((p) => {
    // View mode
    if (currentViewMode === "discounts" && (p.discount_percent || 0) <= 0)
      return false;

    // Store
    if (!activeStores.has(p.store)) return false;

    // Category (from tab or dropdown)
    if (activeCategory && p.category !== activeCategory) return false;

    // Min discount
    if (minDiscount > 0 && (p.discount_percent || 0) < minDiscount)
      return false;

    // Search
    if (searchQuery) {
      const haystack = (
        p.name +
        " " +
        (p.category || "") +
        " " +
        p.store
      ).toLowerCase();
      if (!haystack.includes(searchQuery)) return false;
    }

    return true;
  });

  // Sort
  sortProducts(filteredProducts, currentSort);

  // Update results count
  const countEl = document.getElementById("resultsCount");
  const discountedCount = filteredProducts.filter(
    (p) => (p.discount_percent || 0) > 0,
  ).length;
  countEl.innerHTML = `<span class="font-semibold text-slate-700">${filteredProducts.length}</span> proizvoda`;
  if (discountedCount > 0 && discountedCount < filteredProducts.length) {
    countEl.innerHTML += ` <span class="text-slate-300">|</span> <span class="text-emerald-600 font-medium">${discountedCount} na popustu</span>`;
  }

  // Show/hide clear filters button
  const hasActiveFilters =
    activeCategory ||
    minDiscount > 0 ||
    searchQuery ||
    activeStores.size !==
      [...new Set(allProducts.map((p) => p.store))].length ||
    currentViewMode !== "discounts" ||
    currentSort !== "discount_desc";
  document
    .getElementById("clearFiltersBtn")
    .classList.toggle("hidden", !hasActiveFilters);

  // Render
  displayedCount = 0;
  document.getElementById("productGrid").innerHTML = "";
  loadMore();
}

function sortProducts(products, criterion) {
  products.sort((a, b) => {
    switch (criterion) {
      case "discount_desc":
        return (b.discount_percent || 0) - (a.discount_percent || 0);
      case "discount_asc":
        return (a.discount_percent || 0) - (b.discount_percent || 0);
      case "price_asc":
        return getEffectivePrice(a) - getEffectivePrice(b);
      case "price_desc":
        return getEffectivePrice(b) - getEffectivePrice(a);
      case "name_asc":
        return a.name.localeCompare(b.name, "sr");
      case "name_desc":
        return b.name.localeCompare(a.name, "sr");
      case "savings_desc":
        return getSavings(b) - getSavings(a);
      default:
        return 0;
    }
  });
}

function getEffectivePrice(product) {
  return product.discount_price || product.original_price || 0;
}

function getSavings(product) {
  if (product.original_price && product.discount_price) {
    return product.original_price - product.discount_price;
  }
  return 0;
}

// ---- Lazy Loading ----
function loadMore() {
  const grid = document.getElementById("productGrid");
  const end = Math.min(displayedCount + BATCH_SIZE, filteredProducts.length);
  const fragment = document.createDocumentFragment();

  for (let i = displayedCount; i < end; i++) {
    const card = createProductCard(filteredProducts[i], i);
    fragment.appendChild(card);
  }

  grid.appendChild(fragment);
  displayedCount = end;

  // Toggle load more button
  const loadMoreContainer = document.getElementById("loadMoreContainer");
  const noResults = document.getElementById("noResults");

  if (displayedCount < filteredProducts.length) {
    loadMoreContainer.style.display = "block";
    const loadMoreBtn = document.getElementById("loadMoreBtn");
    loadMoreBtn.innerHTML = `<ph-arrow-down weight="bold" class="text-base"></ph-arrow-down> Ucitaj jos (${filteredProducts.length - displayedCount} preostalo)`;
    loadMoreBtn.className =
      "inline-flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl shadow-sm transition-colors";
  } else {
    loadMoreContainer.style.display = "none";
  }

  noResults.style.display = filteredProducts.length === 0 ? "block" : "none";
}

// ---- Click Tracking ----
const CLICK_STORAGE_KEY = "rssd_clicks";
const CLICK_MAX_ENTRIES = 5000;

function trackClick(product) {
  const discountPct = product.discount_percent || 0;

  // Fire GA4 / Plausible affiliate_click event
  if (window.rssd && window.rssd.trackEvent) {
    window.rssd.trackEvent("affiliate_click", {
      store: product.store,
      product_name: product.name,
      product_id: product.id || "",
      discount_pct: discountPct,
      destination_url: product.product_url,
    });
    // Mark the link so the generic outbound handler in analytics.js skips it
    const buyLink = document.activeElement;
    if (buyLink && buyLink.tagName === "A") {
      buyLink.dataset.analyticsTracked = "1";
    }
  }

  // Persist to localStorage for the on-site analytics dashboard
  try {
    const entry = {
      ts: Date.now(),
      date: new Date().toISOString().slice(0, 10),
      store: product.store,
      productId: product.id,
      productName: product.name,
      url: product.product_url,
      discountPct: discountPct,
    };
    const raw = localStorage.getItem(CLICK_STORAGE_KEY);
    const clicks = raw ? JSON.parse(raw) : [];
    clicks.push(entry);
    // Keep only latest N entries to avoid exceeding storage quota
    if (clicks.length > CLICK_MAX_ENTRIES) clicks.splice(0, clicks.length - CLICK_MAX_ENTRIES);
    localStorage.setItem(CLICK_STORAGE_KEY, JSON.stringify(clicks));
  } catch (_) {
    // localStorage unavailable — silent fail
  }
}

function buildTrackedUrl(product) {
  const storeSlug = (product.store || "unknown")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
  const base = product.product_url;
  const sep = base.includes("?") ? "&" : "?";
  return (
    base +
    sep +
    `utm_source=suplementi_deals&utm_medium=referral&utm_campaign=${storeSlug}&utm_content=${encodeURIComponent(product.id || "product")}`
  );
}

// ---- Product Card Rendering ----
function createProductCard(product, index) {
  const card = document.createElement("article");
  card.className =
    "group bg-white rounded-2xl shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-200 overflow-hidden flex flex-col fade-in-card";
  card.style.animationDelay = `${Math.min(index % BATCH_SIZE, 20) * 30}ms`;

  // UTM tracking with per-store campaign attribution
  const trackedUrl = buildTrackedUrl(product);

  const hasDiscount = product.discount_percent > 0 && product.discount_price;
  const effectivePrice = hasDiscount
    ? product.discount_price
    : product.original_price;
  const savings = hasDiscount
    ? product.original_price - product.discount_price
    : 0;

  // Discount badge color (brand tier system)
  let badgeColor = "";
  if (hasDiscount) {
    if (product.discount_percent >= 30) badgeColor = "bg-red-600";
    else if (product.discount_percent >= 15) badgeColor = "bg-amber-500";
    else badgeColor = "bg-slate-500";
  }

  // Image HTML
  const imageHtml = product.image_url
    ? `<img src="${escapeHtml(product.image_url)}" alt="${escapeHtml(product.name)}" loading="lazy" class="w-full h-full object-contain p-4 group-hover:scale-105 transition-transform duration-300" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
           <div class="absolute inset-0 items-center justify-center text-slate-300 text-sm" style="display:none;">
               <ph-image class="text-3xl"></ph-image>
           </div>`
    : `<div class="flex items-center justify-center text-slate-300">
               <ph-image class="text-3xl"></ph-image>
           </div>`;

  // Discount badge (top-left per brand guidelines)
  const badgeHtml = hasDiscount
    ? `<span class="absolute top-2.5 left-2.5 px-2.5 py-1 rounded-full text-xs font-black text-white ${badgeColor}">-${product.discount_percent}%</span>`
    : "";

  // Out of stock items are pre-filtered, no overlay needed

  // Category badge
  const catColorClass =
    CATEGORY_COLORS[product.category] || "bg-slate-100 text-slate-500";
  const categoryHtml = product.category
    ? `<span class="text-[10px] px-2 py-0.5 ${catColorClass} rounded-full w-fit">${escapeHtml(product.category)}</span>`
    : "";

  // Store colored dot
  const storeColor = STORE_COLORS[product.store] || "#9ca3af";
  const storeHtml = `<div class="flex items-center gap-1.5">
    <span style="background:${storeColor}" class="w-2 h-2 rounded-full shrink-0 inline-block"></span>
    <span class="text-[10px] font-semibold text-[#6b7280] truncate">${escapeHtml(product.store)}</span>
  </div>`;

  // Price section
  let priceHtml = "";
  if (hasDiscount) {
    priceHtml = `
            <div class="flex items-baseline gap-2">
                <span class="text-base font-black text-[#059669]">${formatPrice(product.discount_price)}</span>
                <span class="text-xs text-slate-400 line-through">${formatPrice(product.original_price)}</span>
            </div>
            <p class="text-xs text-[#059669] flex items-center gap-1 mt-0.5 font-semibold">
                <ph-tag size="12"></ph-tag> Ušteda: ${formatPrice(savings)}
            </p>`;
  } else {
    priceHtml = `
            <div>
                <span class="text-base font-black text-slate-900">${formatPrice(product.original_price)}</span>
            </div>`;
  }

  card.innerHTML = `
        <div class="relative bg-slate-50 overflow-hidden" style="aspect-ratio:5/4;">
            ${imageHtml}
            ${badgeHtml}
        </div>
        <div class="p-3 flex-1 flex flex-col gap-1.5">
            ${storeHtml}
            ${categoryHtml}
            <h3 class="text-xs font-semibold text-[#111827] line-clamp-2 flex-1" title="${escapeHtml(product.name)}">${escapeHtml(product.name)}</h3>
            <div class="mt-auto pt-1">
                ${priceHtml}
            </div>
        </div>
        <a href="${escapeHtml(trackedUrl)}" target="_blank" rel="noopener noreferrer"
            class="block text-center text-sm font-bold text-white bg-[#059669] hover:bg-[#047857] px-4 py-3 transition-colors">
            Kupi &rarr;
        </a>
    `;

  // Attach click tracker to the buy link
  const buyLink = card.querySelector("a[target='_blank']");
  if (buyLink) {
    buyLink.addEventListener("click", () => trackClick(product));
  }

  return card;
}

// ---- Utility Functions ----
function formatPrice(price) {
  if (price == null || isNaN(price)) return "";
  return (
    price.toLocaleString("sr-RS", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }) + " RSD"
  );
}

function formatDate(date) {
  return date.toLocaleString("sr-RS", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function truncate(str, maxLen) {
  if (!str) return "";
  return str.length > maxLen ? str.slice(0, maxLen) + "..." : str;
}

function showError(msg) {
  const grid = document.getElementById("productGrid");
  grid.innerHTML = `
        <div class="col-span-full text-center py-16">
            <ph-warning class="text-5xl text-slate-300 mx-auto mb-4"></ph-warning>
            <p class="text-slate-500">${escapeHtml(msg)}</p>
        </div>`;
}

// ---- FAQ Accordion ----
function toggleFaq(button) {
  const answer = button.nextElementSibling;
  const icon = button.querySelector("ph-caret-down");
  const isOpen = !answer.classList.contains("hidden");

  // Close all others
  document
    .querySelectorAll(".faq-answer")
    .forEach((a) => a.classList.add("hidden"));
  document
    .querySelectorAll(".faq-item ph-caret-down")
    .forEach((i) => (i.style.transform = ""));

  if (!isOpen) {
    answer.classList.remove("hidden");
    if (icon) icon.style.transform = "rotate(180deg)";
  }
}

// ---- Newsletter Form Handling ----
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("newsletterForm");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const email = form.querySelector('input[type="email"]').value;
      // Store in localStorage for now (can be replaced with real service later)
      const subs = JSON.parse(localStorage.getItem("rssd_subscribers") || "[]");
      if (!subs.includes(email)) subs.push(email);
      localStorage.setItem("rssd_subscribers", JSON.stringify(subs));
      // Track signup event
      if (window.rssd && window.rssd.trackEvent) {
        window.rssd.trackEvent("newsletter_signup", { page: "popusti" });
      }
      // Show success
      form.innerHTML =
        '<p class="text-white/80 text-sm py-2">Hvala! Uskoro ces primiti prvi pregled popusta.</p>';
    });
  }
});
