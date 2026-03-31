# SEO Brief: suplementi.deals
**Prepared by:** SEO Expert Agent
**Date:** 2026-03-30
**Task:** RSS-28

---

## TASK 1: Technical SEO Audit

### Current State Overview

| Element | Status | Detail |
|---------|--------|--------|
| Title Tag (homepage) | ✅ Good | "Suplementi na Popustu u Srbiji \| RS Supplement Deals" |
| Meta Description (homepage) | ✅ Good | "Jedno mesto za sve popuste na suplementima u Srbiji. Uporedi cene iz 15 online prodavnica." |
| H1 (homepage) | ✅ Good | "Svi suplementi na popustu u Srbiji — na jednom mestu" |
| H1 (popusti page) | ⚠️ Weak | Same as homepage title — should be unique & descriptive |
| H1 (blog post) | ✅ Good | "Najbolji proteini u Srbiji 2026 — Vodic za kupovinu" |
| Schema: WebSite | ✅ Present | With SearchAction (good for AI engines) |
| Schema: FAQPage | ✅ Present | On homepage and /popusti/ |
| Schema: BlogPosting | ✅ Present | On blog posts (date, org) |
| Schema: Product | ❌ Missing | No Product schema on /popusti/ product listings |
| Schema: Organization | ❌ Missing | Not present anywhere |
| Schema: BreadcrumbList | ❌ Missing | No breadcrumbs on any page |
| Schema: ItemList | ❌ Missing | Not on /popusti/ category |
| Canonical Tags | ❌ Missing | No canonical tags found on any page |
| Open Graph / Twitter Card | ❌ Missing | No OG/Twitter meta tags |
| Sitemap | ✅ Present | At /sitemap.xml, referenced in robots.txt |
| Robots.txt | ✅ Good | Allow: /, all bots permitted |
| Internal Navigation | ⚠️ Minimal | Only 3 nav links (Popusti, Blog, O sajtu) |
| Blog Internal Links | ⚠️ Weak | Blog posts only link to /popusti/ and /blog/ — no category cross-links |
| Page Count in Sitemap | ❌ Thin | Only 5 URLs total — very thin for SEO authority |

---

### Critical Fixes (Prioritized by Impact)

#### P1 — HIGH IMPACT (Fix immediately)

**1. Add canonical tags to all pages**
```html
<!-- Each page needs its own canonical -->
<link rel="canonical" href="https://suplementi.deals/popusti/" />
```
Without canonicals, Google may treat similar content as duplicate. The /popusti/ page and homepage share nearly identical title/meta.

**2. Fix /popusti/ page — unique title + meta + H1**
```html
<!-- Current (WRONG): -->
<title>Suplementi na Popustu u Srbiji | RS Supplement Deals</title>
<!-- Fix: -->
<title>Popusti na Suplementima u Srbiji — Uporedi Cene | RS Supplement Deals</title>
<meta name="description" content="Pronađi najbolje popuste na proteine, kreatin, vitamine i pre-workout iz 15 srpskih prodavnica. Ažurirano svakih 6 sati." />
<h1>Popusti na suplementima — 15 prodavnica, ažurirano svakih 6 sati</h1>
```

**3. Add Open Graph + Twitter Card meta tags (critical for AI sharing & AIO)**
```html
<!-- Homepage -->
<meta property="og:type" content="website" />
<meta property="og:title" content="Suplementi na Popustu u Srbiji | RS Supplement Deals" />
<meta property="og:description" content="Jedno mesto za sve popuste na suplementima u Srbiji. Uporedi cene iz 15 online prodavnica." />
<meta property="og:url" content="https://suplementi.deals/" />
<meta property="og:image" content="https://suplementi.deals/og-image.jpg" />
<meta name="twitter:card" content="summary_large_image" />
```

#### P2 — HIGH IMPACT (Fix this sprint)

**4. Add Organization schema to homepage**
See Task 4 for copy-paste JSON-LD.

**5. Add Product + Offer schema to each product listing on /popusti/**
The site already has structured product data (price, store, discount %) — this just needs to be output as JSON-LD. See Task 4.

**6. Add BreadcrumbList schema to blog posts and category pages**
See Task 4.

#### P3 — MEDIUM IMPACT (Next sprint)

**7. Expand sitemap** — Currently only 5 URLs. Every blog post, category page, and future content should be in sitemap.xml.

**8. Add category pages to navigation and sitemap**
Currently there are no dedicated pages for: whey protein, kreatin, pre-workout, BCAA, vitamini, protein bar, mass gainer. These must be created as indexable URLs (see Task 2).

**9. Internal linking on blog posts**
The existing blog posts (krediti vodič, proteini vodič) only link back to /popusti/ generically. They need to link to specific category pages once those exist.

**10. Add `lang="sr"` or `lang="sr-Latn"` if not already present**
Already noted as "sr-Latn" in language attribute — confirm this is on `<html>` tag.

---

## TASK 2: Content Cluster Taxonomy

### Hub-and-Spoke Architecture

```
HOMEPAGE (Hub)
"Suplementi na Popustu u Srbiji — na jednom mestu"
Price comparison authority. Links OUT to all Primary Spokes.
Links IN from: all category pages, all blog posts

     ├── PRIMARY SPOKE: /kategorija/proteini/
     │       Whey protein, kazein, veganski protein
     │       Links to: blog/proteini-vodic, blog/whey-vs-izolat, blog/veganski-proteini
     │
     ├── PRIMARY SPOKE: /kategorija/kreatin/
     │       Kreatin monohidrat, Kre-Alkalyn
     │       Links to: blog/kreatin-za-pocetnike, blog/kako-dozirati-kreatin
     │
     ├── PRIMARY SPOKE: /kategorija/pre-workout/
     │       Pre-workout dodaci
     │       Links to: blog/pre-workout-vodic, blog/koji-pre-workout-izabrati
     │
     ├── PRIMARY SPOKE: /kategorija/bcaa/
     │       BCAA, EAA amino kiseline
     │       Links to: blog/bcaa-vodic, blog/oporavak-posle-treninga
     │
     ├── PRIMARY SPOKE: /kategorija/vitamini/
     │       Multivitamini, vitamin D, omega-3
     │       Links to: blog/vitamini-za-sportiste, blog/omega-3-srbija
     │
     ├── PRIMARY SPOKE: /kategorija/protein-bar/
     │       Proteinski barovi i snaci
     │       Links to: blog/proteinski-barovi-srbija, blog/zdrave-uzine-za-sportiste
     │
     └── PRIMARY SPOKE: /kategorija/mass-gainer/
             Gaineri i mase
             Links to: blog/mass-gainer-vodic, blog/kaloricni-suficit-srbija
```

### Secondary Spokes (Blog Cluster)

| Blog Post Title | Maps To Category | Buying Intent | Bidirectional Links Required |
|-----------------|-----------------|---------------|------------------------------|
| Najbolji proteini u Srbiji 2026 (EXISTS) | /kategorija/proteini/ | High | → proteini, kreatin (2+ categories) |
| Kreatin: Kompletni vodič za početnike (EXISTS) | /kategorija/kreatin/ | Medium-High | → kreatin, proteini |
| Whey protein vs. izolat — šta izabrati? (NEW) | /kategorija/proteini/ | High | → proteini, mass-gainer |
| Veganski proteini u Srbiji 2026 (NEW) | /kategorija/proteini/ | Medium | → proteini, vitamini |
| Pre-workout suplementi — vodič (NEW) | /kategorija/pre-workout/ | High | → pre-workout, bcaa |
| BCAA i oporavak posle treninga (NEW) | /kategorija/bcaa/ | Medium | → bcaa, proteini |
| Vitamini za sportiste — šta je zaista potrebno (NEW) | /kategorija/vitamini/ | Medium | → vitamini, proteini |
| Mass gainer vodič za početnike (NEW) | /kategorija/mass-gainer/ | High | → mass-gainer, proteini, kreatin |
| Pregled prodavnica suplemenata u Srbiji (NEW) | Homepage | Informational | → homepage, sve kategorije |
| Jesenji/Zimski deals roundup (SEASONAL) | Homepage | High | → homepage, sve kategorije |
| Proteinski barovi Srbija — top 10 (NEW) | /kategorija/protein-bar/ | High | → protein-bar, proteini |

### Bidirectional Internal Linking Rules

**Every blog post MUST:**
- Link to 2+ category pages (contextual, anchor text = keyword)
- Link to homepage with "uporedi cene" anchor text
- Link to 1-2 related blog posts

**Every category page MUST:**
- Link back to homepage
- Link to 3+ related blog posts
- Link to 2+ adjacent categories (e.g., proteini → kreatin, mass-gainer)

**Homepage MUST:**
- Link to all 7 primary category pages
- Link to latest 3-4 blog posts (already partially done via "Korisni vodiči" section)

---

## TASK 3: Keyword Map (Serbian Language)

### Primary Keywords (High Volume, High Intent)

| # | Keyword | Language | Page Type | Intent | Competition | Priority |
|---|---------|----------|-----------|--------|-------------|----------|
| 1 | whey protein cena Srbija | SR | /kategorija/proteini/ | Buying | Medium | P1 |
| 2 | kreatin cena Srbija | SR | /kategorija/kreatin/ | Buying | Medium | P1 |
| 3 | suplementi na popustu Srbija | SR | Homepage | Buying | Low | P1 |
| 4 | jeftini suplementi Srbija | SR | Homepage | Buying | Low | P1 |
| 5 | proteini cena Srbija | SR | /kategorija/proteini/ | Buying | Medium | P1 |
| 6 | pre workout Srbija | SR | /kategorija/pre-workout/ | Buying | Medium | P1 |
| 7 | BCAA cena Srbija | SR | /kategorija/bcaa/ | Buying | Low | P1 |
| 8 | mass gainer Srbija | SR | /kategorija/mass-gainer/ | Buying | Medium | P1 |
| 9 | vitamini za sportiste Srbija | SR | /kategorija/vitamini/ | Buying | Low | P1 |
| 10 | proteinski bar Srbija | SR | /kategorija/protein-bar/ | Buying | Low | P1 |

### Long-Tail Buying Queries

| # | Keyword | Page Type | Intent | Notes |
|---|---------|-----------|--------|-------|
| 11 | whey protein jeftino Srbija | /kategorija/proteini/ | Buying | "jeftino" = high deal intent |
| 12 | kreatin monohidrat cena Srbija | /kategorija/kreatin/ | Buying | Specific form, high intent |
| 13 | whey izolat cena Srbija | /kategorija/proteini/ | Buying | Premium segment |
| 14 | whey [brand] cena Srbija | Product pages | Buying | Brand-specific — add per brand |
| 15 | kreatin akcija popust Srbija | /kategorija/kreatin/ | Buying | "akcija/popust" = deal seeker |
| 16 | veganski protein Srbija cena | /kategorija/proteini/ | Buying | Growing niche |
| 17 | gainer za masu Srbija | /kategorija/mass-gainer/ | Buying | Popular phrasing |
| 18 | proteinski barovi Srbija kupovina | /kategorija/protein-bar/ | Buying | Snack/convenience intent |
| 19 | omega 3 cena Srbija | /kategorija/vitamini/ | Buying | High year-round volume |
| 20 | creatine srbija online | /kategorija/kreatin/ | Buying | English query from SR users |
| 21 | suplementi srbija online kupovina | Homepage | Buying | Broad category |
| 22 | gde kupiti whey protein Srbija | Blog: proteini vodic | Research | "gde kupiti" = near-decision |
| 23 | gde kupiti kreatin jeftino | Blog: kreatin vodic | Research | High affiliate value |
| 24 | koji proteini su najbolji Srbija | Blog: proteini vodic | Research | "koji" = research intent |
| 25 | koji kreatin izabrati | Blog: kreatin vodic | Research | Common question |

### AIO-Targeted Queries (AI Overview / Perplexity / Copilot)

These are phrased as questions AI engines love to answer. Use these as H2/H3 headings + FAQ schema in blog posts.

| # | Keyword / Question | Page Type | AI Engine Value |
|---|-------------------|-----------|----------------|
| 26 | kako odabrati whey protein | Blog: proteini vodic | High — direct FAQ |
| 27 | kako dozirati kreatin monohidrat | Blog: kreatin vodic | High — how-to |
| 28 | koji suplementi su neophodni za početnika | Blog: vodic za pocetnike (NEW) | High — listicle |
| 29 | gde su najpovoljniji suplementi u Srbiji | Homepage | High — comparison |
| 30 | da li se isplati uzimati BCAA | Blog: bcaa vodic | Medium — debate |
| 31 | kako izabrati pre workout | Blog: pre-workout vodic | High |
| 32 | koji vitamini su korisni za trening | Blog: vitamini vodic | High |
| 33 | šta je mass gainer i za koga je | Blog: gainer vodic | High |
| 34 | koliko proteina treba dnevno | Blog: proteini vodic (add section) | High — in existing post |
| 35 | da li su proteinski barovi zdravi | Blog: protein bar | Medium |

### Competitor Keywords to Target (Gaps)

Sites ranking now: cenesuplemenata.rs, proteinisrbija.rs, supplementstore.rs, lama.rs, ananas.rs

suplementi.deals opportunity: **none of these competitors focus on "popust/akcija/jeftino" + cross-store comparison**. That is the unique SEO angle to own.

Priority query cluster to dominate first:
- "suplementi popust srbija" (no strong competitor)
- "uporedi cene suplemenata srbija" (no strong competitor)
- "suplementi akcija srbija" (scattered results)

---

## TASK 4: Schema Markup Templates (Copy-Paste Ready JSON-LD)

### Homepage Schema

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://suplementi.deals/#organization",
      "name": "RS Supplement Deals",
      "url": "https://suplementi.deals/",
      "description": "Jedno mesto za sve popuste na suplementima u Srbiji. Poredimo cene iz 15 online prodavnica.",
      "inLanguage": "sr-Latn"
    },
    {
      "@type": "WebSite",
      "@id": "https://suplementi.deals/#website",
      "url": "https://suplementi.deals/",
      "name": "Suplementi na Popustu u Srbiji | RS Supplement Deals",
      "publisher": {
        "@id": "https://suplementi.deals/#organization"
      },
      "potentialAction": {
        "@type": "SearchAction",
        "target": {
          "@type": "EntryPoint",
          "urlTemplate": "https://suplementi.deals/popusti/?q={search_term_string}"
        },
        "query-input": "required name=search_term_string"
      }
    },
    {
      "@type": "SiteNavigationElement",
      "name": ["Popusti", "Blog", "O Sajtu"],
      "url": [
        "https://suplementi.deals/popusti/",
        "https://suplementi.deals/blog/",
        "https://suplementi.deals/#o-sajtu"
      ]
    }
  ]
}
</script>
```

### Product Page Schema (for each product listing on /popusti/)

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "{{product_name}}",
  "image": "{{product_image_url}}",
  "description": "{{product_name}} na popustu u Srbiji. Pronađi best cenu iz {{store_name}}.",
  "brand": {
    "@type": "Brand",
    "name": "{{brand_name}}"
  },
  "offers": {
    "@type": "Offer",
    "url": "{{product_affiliate_url}}",
    "priceCurrency": "RSD",
    "price": "{{discount_price}}",
    "priceValidUntil": "{{date_scraped_plus_7_days}}",
    "availability": "https://schema.org/InStock",
    "seller": {
      "@type": "Organization",
      "name": "{{store_name}}",
      "url": "{{store_url}}"
    }
  }
}
</script>
```

### Category Page Schema (/kategorija/proteini/ etc.)

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        {
          "@type": "ListItem",
          "position": 1,
          "name": "Početna",
          "item": "https://suplementi.deals/"
        },
        {
          "@type": "ListItem",
          "position": 2,
          "name": "{{category_name}}",
          "item": "https://suplementi.deals/kategorija/{{category_slug}}/"
        }
      ]
    },
    {
      "@type": "ItemList",
      "name": "{{category_name}} na popustu u Srbiji",
      "description": "Uporedi cene {{category_name}} iz 15 prodavnica u Srbiji.",
      "url": "https://suplementi.deals/kategorija/{{category_slug}}/",
      "numberOfItems": "{{item_count}}",
      "itemListElement": [
        {
          "@type": "ListItem",
          "position": 1,
          "url": "{{first_product_affiliate_url}}",
          "name": "{{first_product_name}}"
        }
      ]
    }
  ]
}
</script>
```

### Blog Post Schema

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Article",
      "@id": "https://suplementi.deals/blog/{{post-slug}}.html#article",
      "headline": "{{post_title}}",
      "description": "{{meta_description}}",
      "image": "https://suplementi.deals/images/{{post-slug}}-og.jpg",
      "author": {
        "@type": "Organization",
        "name": "RS Supplement Deals",
        "@id": "https://suplementi.deals/#organization"
      },
      "publisher": {
        "@type": "Organization",
        "name": "RS Supplement Deals",
        "@id": "https://suplementi.deals/#organization"
      },
      "datePublished": "{{YYYY-MM-DD}}",
      "dateModified": "{{YYYY-MM-DD}}",
      "inLanguage": "sr-Latn",
      "mainEntityOfPage": {
        "@type": "WebPage",
        "@id": "https://suplementi.deals/blog/{{post-slug}}.html"
      }
    },
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        {
          "@type": "ListItem",
          "position": 1,
          "name": "Početna",
          "item": "https://suplementi.deals/"
        },
        {
          "@type": "ListItem",
          "position": 2,
          "name": "Blog",
          "item": "https://suplementi.deals/blog/"
        },
        {
          "@type": "ListItem",
          "position": 3,
          "name": "{{post_title}}",
          "item": "https://suplementi.deals/blog/{{post-slug}}.html"
        }
      ]
    },
    {
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "{{question_1}}",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "{{answer_1}}"
          }
        },
        {
          "@type": "Question",
          "name": "{{question_2}}",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "{{answer_2}}"
          }
        }
      ]
    }
  ]
}
</script>
```

---

## Quick Win Summary for Engineer

| Fix | Effort | SEO Impact |
|-----|--------|------------|
| Add canonical tags | 30 min | High |
| Add OG/Twitter meta | 30 min | High (AI sharing) |
| Fix /popusti/ title/meta/H1 | 15 min | High |
| Add Organization schema to homepage | 15 min | Medium-High |
| Add Product+Offer schema to product listings | 2-4 hrs | High |
| Add BreadcrumbList to blog+category | 1 hr | Medium |
| Create 7 category pages | 4-8 hrs | Critical for ranking |
| Expand sitemap to all pages | 1 hr | Medium |
| Add internal links in existing blog posts | 1 hr | Medium |
| Create 5 AIO-targeted blog posts | 5+ hrs | High (AI traffic) |
