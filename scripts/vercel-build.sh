#!/usr/bin/env bash
# Vercel build script for suplementi.deals
# Runs the scraper and generates the static _site/ directory

set -e

echo "==> Setting up output directories..."
mkdir -p _site/popusti _site/blog

echo "==> Running scraper (best-effort, failures allowed)..."
python supplement_scraper.py --no-dashboard 2>/dev/null || true

echo "==> Generating popusti page..."
python -c "
import json, os

data_path = 'data/supplements.json'
if os.path.exists(data_path):
    with open(data_path, 'r') as f:
        data = json.load(f)
else:
    from datetime import datetime
    data = {
        'scraped_at': datetime.now().isoformat(),
        'stores_scraped': [],
        'stores_failed': ['All stores - scraping in progress'],
        'total_products': 0,
        'total_discounted': 0,
        'products': [],
        'weekly_summary': {
            'total_products': 0,
            'total_discounted': 0,
            'avg_discount_percent': 0,
            'top_discounts': [],
            'by_store': {},
            'by_category': {},
            'new_discounts_count': 0,
            'ended_discounts_count': 0,
            'deeper_discounts_count': 0,
        }
    }

with open('supplement_dashboard.html', 'r') as f:
    template = f.read()
json_str = json.dumps(data, ensure_ascii=False)
output = template.replace('/* __SUPPLEMENT_DATA_PLACEHOLDER__ */', json_str)
with open('_site/popusti/index.html', 'w') as f:
    f.write(output)
print('Generated _site/popusti/index.html')
"

echo "==> Generating landing page..."
python -c "
import json, os, html as html_mod

data_path = 'data/supplements.json'
products = []
total_products = 0
total_discounted = 0
if os.path.exists(data_path):
    with open(data_path, 'r') as f:
        d = json.load(f)
    products = d.get('products', [])
    total_products = len(products)
    deals = [p for p in products if p.get('in_stock', True) and p.get('discount_percent', 0) >= 20 and p.get('image_url')]
    deals.sort(key=lambda x: x.get('discount_percent', 0), reverse=True)
    top6 = deals[:6]
    total_discounted = len([p for p in products if p.get('discount_percent', 0) > 0 and p.get('in_stock', True)])
else:
    top6 = []

cards_html = ''
for p in top6:
    name = html_mod.escape(p.get('name', '')[:40])
    store = html_mod.escape(p.get('store', ''))
    img = html_mod.escape(p.get('image_url', ''))
    pct = p.get('discount_percent', 0)
    price = p.get('discount_price') or p.get('original_price') or 0
    orig = p.get('original_price') or 0
    url = html_mod.escape(p.get('product_url', '#'))
    utm_url = url + ('&amp;' if '?' in p.get('product_url', '#') else '?') + 'utm_source=rssupplementdeals&amp;utm_medium=referral&amp;utm_campaign=featured'
    cards_html += f'''
    <div class=\"bg-white rounded-md border border-[#d0d0d0] overflow-hidden hover:shadow-md transition-shadow flex flex-col\">
      <div class=\"relative\">
        <div class=\"aspect-square bg-[#f5f5f5] flex items-center justify-center overflow-hidden\">
          <img src=\"{img}\" alt=\"{name}\" loading=\"lazy\" class=\"w-full h-full object-contain p-2\" onerror=\"this.style.display='none';this.nextElementSibling.style.display='flex';\">
          <div class=\"absolute inset-0 items-center justify-center text-[#d0d0d0]\" style=\"display:none;\"><ph-package weight=\"duotone\" class=\"text-5xl\"></ph-package></div>
        </div>
        <span class=\"absolute top-2 left-2 bg-red-600 text-white text-xs font-bold px-2 py-0.5 rounded\">-{pct}%</span>
      </div>
      <div class=\"p-3 flex flex-col flex-1\">
        <p class=\"text-xs text-[#999] mb-1\">{store}</p>
        <h3 class=\"text-xs font-semibold text-[#333] line-clamp-2 mb-2 flex-1\">{name}</h3>
        <div class=\"flex items-baseline gap-1.5 mb-2\">
          <span class=\"text-sm font-bold text-[#333]\">{int(price):,} RSD</span>
          <span class=\"text-xs text-[#999] line-through\">{int(orig):,} RSD</span>
        </div>
        <a href=\"{utm_url}\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"w-full block text-center py-1.5 bg-[#606060] text-white text-xs font-semibold rounded hover:bg-[#505050] transition-colors\">Kupi</a>
      </div>
    </div>'''

with open('landing.html', 'r') as f:
    landing = f.read()
landing = landing.replace('<!-- __FEATURED_DEALS_PLACEHOLDER__ -->', cards_html)
landing = landing.replace('480+ popusta', f'{total_discounted}+ popusta')
landing = landing.replace('900+ proizvoda', f'{total_products}+ proizvoda')
with open('_site/index.html', 'w') as f:
    f.write(landing)
print('Generated _site/index.html')
"

echo "==> Copying static assets..."
cp blog/*.html _site/blog/ 2>/dev/null || true
cp -r assets _site/assets 2>/dev/null || true
cp robots.txt _site/robots.txt 2>/dev/null || true
cp sitemap.xml _site/sitemap.xml 2>/dev/null || true
cp vercel.json _site/vercel.json 2>/dev/null || true

echo "==> Build complete. Contents of _site/:"
ls _site/
