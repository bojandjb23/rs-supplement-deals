/**
 * RS Supplement Deals — Analytics Module
 *
 * Provides:
 *  - Google Analytics 4 (GA4) via gtag.js
 *  - Plausible analytics (optional, privacy-friendly alternative)
 *  - window.rssd.trackEvent() — unified event API used by supplement-dashboard.js
 *
 * Configuration (add to <head> before this script):
 *   <meta name="ga4-id" content="G-XXXXXXXXXX">       ← GA4 measurement ID
 *   <meta name="plausible-domain" content="suplementi.deals">  ← Plausible domain (optional)
 *
 * Events fired:
 *   affiliate_click     — "Kupi" button clicked; params: store, product_name, product_id, discount_pct, destination_url
 *   newsletter_signup   — email signup form submitted
 *   product_card_click  — product card body clicked (not the buy button)
 *   filter_applied      — user applies a filter (category, store, discount range, search)
 *   view_item_list      — initial page load showing product list (GA4 ecommerce)
 */

(function () {
  "use strict";

  // ── Read config from meta tags ──────────────────────────────────────────────
  const ga4Id = document
    .querySelector('meta[name="ga4-id"]')
    ?.getAttribute("content")
    ?.trim();

  const plausibleDomain = document
    .querySelector('meta[name="plausible-domain"]')
    ?.getAttribute("content")
    ?.trim();

  // ── Load GA4 ──────────────────────────────────────────────────────────────
  function loadGA4(measurementId) {
    if (!measurementId || measurementId === "G-XXXXXXXXXX") return;

    const script = document.createElement("script");
    script.async = true;
    script.src = "https://www.googletagmanager.com/gtag/js?id=" + measurementId;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    window.gtag = function () {
      dataLayer.push(arguments);
    };
    gtag("js", new Date());
    gtag("config", measurementId, {
      // Respect user privacy — anonymize IPs
      anonymize_ip: true,
      // Don't send page_view twice on SPA navigation (we handle it manually)
      send_page_view: true,
    });
  }

  // ── Load Plausible ────────────────────────────────────────────────────────
  function loadPlausible(domain) {
    if (!domain) return;

    const script = document.createElement("script");
    script.defer = true;
    script.setAttribute("data-domain", domain);
    script.src = "https://plausible.io/js/plausible.outbound-links.js";
    document.head.appendChild(script);
    // Plausible queue for custom events
    window.plausible =
      window.plausible ||
      function () {
        (window.plausible.q = window.plausible.q || []).push(arguments);
      };
  }

  // ── Unified event API ─────────────────────────────────────────────────────
  function trackEvent(eventName, params) {
    params = params || {};

    // GA4
    if (typeof window.gtag === "function") {
      window.gtag("event", eventName, params);
    }

    // Plausible (maps to custom event)
    if (typeof window.plausible === "function") {
      window.plausible(eventName, { props: params });
    }
  }

  // ── Auto-track outbound affiliate clicks ─────────────────────────────────
  // Fires on any <a target="_blank"> that points to an external domain.
  // supplement-dashboard.js also calls trackEvent('affiliate_click') directly
  // with richer product metadata — this is a fallback for links we can't
  // instrument explicitly (e.g., homepage featured cards).
  function setupOutboundLinkTracking() {
    document.addEventListener("click", function (e) {
      const link = e.target.closest("a[target='_blank']");
      if (!link) return;

      const href = link.href || "";
      if (!href.startsWith("http")) return;

      // Skip internal links
      try {
        const linkHost = new URL(href).hostname;
        if (linkHost === location.hostname) return;

        // Only fire if not already tracked by the richer supplement-dashboard handler
        if (link.dataset.analyticsTracked) return;

        // Derive store name from UTM campaign param if present
        let store = "unknown";
        try {
          const urlParams = new URL(href).searchParams;
          const campaign = urlParams.get("utm_campaign");
          if (campaign) store = campaign.replace(/_/g, " ");
        } catch (_) {}

        trackEvent("affiliate_click", {
          store: store,
          destination_url: href,
          link_text: (link.textContent || "").trim().slice(0, 50),
        });
      } catch (_) {}
    });
  }

  // ── Expose public API ─────────────────────────────────────────────────────
  window.rssd = window.rssd || {};
  window.rssd.trackEvent = trackEvent;

  // ── Bootstrap ─────────────────────────────────────────────────────────────
  loadGA4(ga4Id);
  loadPlausible(plausibleDomain);
  setupOutboundLinkTracking();
})();
