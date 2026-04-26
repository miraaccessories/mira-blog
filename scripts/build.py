#!/usr/bin/env python3
"""
Mira Blog — Static Site Generator
Post format: /posts/YYYY-MM-DD-slug.html
Each post has a META comment block at the top, then raw HTML body.
Run: python3 scripts/build.py
Output: dist/
"""

import hashlib, json, os, re, shutil, sys
from datetime import datetime
from pathlib import Path


def _file_hash(p):
    """Short MD5 of file content for cache-busting query strings."""
    try:
        return hashlib.md5(Path(p).read_bytes()).hexdigest()[:8]
    except FileNotFoundError:
        return "0"


def _load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

_load_env()

SITE = {
    "name":        "Mira Accessories Blog",
    "url":         "https://blog.miraaccessories.co.za",
    "shop_url":    "https://www.miraaccessories.co.za",
    "description": "Expert advice on baby and toddler hair care, styling tips, and the best hair accessories for South African moms.",
    "locale":      "en-ZA",
    "country":     "ZA",
    "ga4_id":      os.environ.get("MIRA_GA4_ID", "G-DP1X3Q0NST"),
    "gsc_verify":  os.environ.get("MIRA_GSC_VERIFY", ""),
    "instagram":   os.environ.get("MIRA_INSTAGRAM", "https://www.instagram.com/miraaccessories.co.za/"),
    "facebook":    os.environ.get("MIRA_FACEBOOK", ""),
}

AUTHOR = {
    "name":  "Shaveta V Sahoo",
    "title": "Co-founder, Mira Accessories",
    "bio":   "Shaveta V Sahoo is the co-founder of Mira Accessories, South Africa's premium baby hair accessory brand. An engineer by training and a mom by calling, she designs accessories that are safe, gentle, and made to last — and writes for South African moms navigating the messy, magical years of raising little girls.",
    "byline_bio": "Mom to a little girl, engineer, and co-founder of Mira Accessories. Writing from Johannesburg about the small, sacred parts of raising a daughter.",
    "url":   "/about/",
    "image": "",
}

ROOT, POSTS_DIR, STATIC_DIR, DIST_DIR = (
    Path(__file__).parent.parent,
    Path(__file__).parent.parent / "posts",
    Path(__file__).parent.parent / "static",
    Path(__file__).parent.parent / "dist",
)
PER_PAGE = 9


# ── HELPERS ─────────────────────────────────────────
def slugify(t):
    t = re.sub(r'<[^>]+>', '', str(t)).lower().strip()
    t = re.sub(r'[^\w\s-]', '', t)
    return re.sub(r'[\s_]+', '-', t).strip('-')

def esc(s):
    return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')


_WIX_FILL_RE = re.compile(r'(/v1/)(fill|fit)/w_\d+,h_\d+(,[^/]+)?/')

def wix_img(url, w, h, align="c", mode="fill"):
    """Rewrite a Wix CDN image URL to request a specific width/height.
    mode: 'fill' crops to exact dimensions (default);
          'fit' scales to fit within dimensions, preserves full image (letterbox-friendly).
    align: 'c' center (default), 't' top, 'b' bottom, 'l' left, 'r' right.
    Falls through untouched for non-Wix URLs or unexpected formats."""
    if not url or "static.wixstatic.com" not in url:
        return url
    return _WIX_FILL_RE.sub(rf'\1{mode}/w_{w},h_{h},al_{align},q_80/', url)

def wix_srcset(url, widths, aspect=1, align="c", mode="fill"):
    """Build a responsive srcset value listing the same image at multiple widths.
    aspect: width/height ratio (1 for square, 1.5 for 3:2, etc.)
    Falls through to single URL if not a Wix URL."""
    if not url or "static.wixstatic.com" not in url:
        return url
    return ", ".join(f"{wix_img(url, w, int(w/aspect), align, mode)} {w}w" for w in widths)


# ── POST LOADER ─────────────────────────────────────
def load_posts(src_dir=None, url_prefix="/posts/"):
    src_dir = src_dir or POSTS_DIR
    posts = []
    for f in src_dir.glob("*.html"):
        raw = f.read_text(encoding="utf-8")
        meta = {}
        m = re.search(r'<!--META\n(.*?)-->', raw, re.DOTALL)
        if m:
            for line in m.group(1).strip().splitlines():
                if ':' in line:
                    k, _, v = line.partition(':')
                    meta[k.strip()] = v.strip()
        meta['tags']     = [t.strip() for t in meta.get('tags','').split(',') if t.strip()]
        meta['keywords'] = [k.strip() for k in meta.get('keywords','').split(',') if k.strip()]
        meta['featured'] = meta.get('featured','').strip().lower() in ('true','1','yes')
        body = re.sub(r'<!--META\n.*?-->', '', raw, flags=re.DOTALL).strip()
        excerpt = meta.get('excerpt', re.sub(r'<[^>]+>','',body)[:160].strip()+'...')
        posts.append({**meta, 'slug': f.stem, 'url': f'{url_prefix}{f.stem}/',
                      'body': body, 'excerpt': excerpt})
    posts.sort(key=lambda p: p.get('date',''), reverse=True)
    return posts


# ── COMPONENTS ──────────────────────────────────────
def post_card(p):
    return f'''<a class="post-card" href="{p['url']}">
  <div class="post-card__image-wrap">
    <img class="post-card__image" src="{wix_img(p.get('image',''), 600, 400)}" alt="{esc(p.get('image_alt', p.get('title','')))}" loading="lazy" width="600" height="400">
  </div>
  <div class="post-card__body">
    <div class="post-card__category">{p.get('category','')}</div>
    <h2 class="post-card__title">{esc(p.get('title',''))}</h2>
    <p class="post-card__excerpt">{esc(p.get('excerpt',''))}</p>
    <div class="post-card__footer">
      <span class="post-card__meta">{p.get('read_time','5 min read')}</span>
      <span class="post-card__read">Read more →</span>
    </div>
  </div>
</a>'''

def featured_card(p):
    return f'''<a class="featured-post" href="{p['url']}">
  <img class="featured-post__image" src="{wix_img(p.get('image',''), 800, 600)}" alt="{esc(p.get('image_alt', p.get('title','')))}" width="800" height="600" loading="eager">
  <div class="featured-post__body">
    <span class="post-category-tag">{p.get('category','')}</span>
    <h2 class="featured-post__title">{esc(p.get('title',''))}</h2>
    <p class="featured-post__excerpt">{esc(p.get('excerpt',''))}</p>
    <div class="featured-post__meta">
      <span>{p.get('date','')}</span>
      <span>{p.get('read_time','5 min read')}</span>
    </div>
    <span class="read-more-link">Read article</span>
  </div>
</a>'''

def sidebar_post(p):
    return f'''<a class="sidebar-post" href="{p['url']}">
  <img src="{wix_img(p.get('image',''), 104, 104)}" alt="{esc(p.get('title',''))}" loading="lazy" width="52" height="52">
  <div>
    <div class="sidebar-post__title">{esc(p.get('title',''))}</div>
    <div class="sidebar-post__cat">{p.get('category','')}</div>
  </div>
</a>'''

def related_section(post, all_posts):
    tags, cat = set(post.get('tags',[])), post.get('category','')
    scored = sorted(
        [(len(tags & set(p.get('tags',[]))) + (2 if p.get('category')==cat else 0), p)
         for p in all_posts if p['slug'] != post['slug'] and
         (len(tags & set(p.get('tags',[]))) + (2 if p.get('category')==cat else 0)) > 0],
        key=lambda x: x[0], reverse=True
    )
    related = [p for _,p in scored[:3]] or [p for p in all_posts if p['slug']!=post['slug']][:3]
    return f'''<div class="related-posts"><div class="container">
  <div class="section-header">
    <div><h2 class="section-title">You might also like</h2><p class="section-subtitle">More tips for SA moms</p></div>
    <a href="/posts/" class="view-all">All posts →</a>
  </div>
  <div class="post-grid">{"".join(post_card(p) for p in related)}</div>
</div></div>'''

def toc(html):
    hs = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
    if len(hs) < 3: return ''
    items = ''.join(f'<a class="toc-item" href="#{slugify(h)}">{re.sub(r"<[^>]+>","",h).strip()}</a>' for h in hs)
    return f'<div class="sidebar-widget"><div class="sidebar-widget__title">In this article</div>{items}</div>'

def add_ids(html):
    def ai(m):
        txt = re.sub(r'<[^>]+>','',m.group(1)).strip()
        return f'<h2 id="{slugify(txt)}">{m.group(1)}</h2>'
    return re.sub(r'<h2[^>]*>(.*?)</h2>', ai, html, flags=re.DOTALL)

def search_idx(posts):
    idx = [{'title':p.get('title',''),'url':p.get('url',''),'excerpt':p.get('excerpt',''),
            'category':p.get('category',''),'tags':p.get('tags',[]),
            'image':p.get('image',''),
            'content':re.sub(r'<[^>]+>','',p.get('body',''))[:500]} for p in posts]
    return f'window.SEARCH_INDEX={json.dumps(idx, ensure_ascii=False)};'


# ── SHELL ────────────────────────────────────────────
def shell(title, desc, og_img, canonical, content, posts, extra=''):
    cats = {}
    for p in posts:
        c = p.get('category','')
        if c: cats[c] = cats.get(c,0)+1

    nav = '\n'.join(f'<a href="{u}">{l}</a>' for l,u in [
        ('All Posts','/posts/'),('School Hair','/category/school-hair/'),
        ('Baby Care','/category/baby-care/'),('Gift Ideas','/category/gift-ideas/'),
        ('Mom &amp; Baby','/category/mom-baby/'),('Photoshoots','/category/photoshoots/'),
    ])
    footer_cats = ''.join(f'<a href="/category/{slugify(c)}/">{c}</a>' for c in cats)
    year = datetime.now().year

    gsc  = f'<meta name="google-site-verification" content="{SITE["gsc_verify"]}">' if SITE.get("gsc_verify") else ''
    ga4  = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={SITE["ga4_id"]}"></script>'
            f'<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","{SITE["ga4_id"]}");</script>') if SITE.get("ga4_id") else ''
    return f'''<!DOCTYPE html>
<html lang="{SITE["locale"]}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{SITE["url"]}{canonical}">
<link rel="alternate" hreflang="en-za" href="{SITE["url"]}{canonical}">
<link rel="alternate" hreflang="x-default" href="{SITE["url"]}{canonical}">
<meta name="geo.region" content="ZA">
<meta name="geo.placename" content="South Africa">
<meta http-equiv="content-language" content="en-ZA">
{gsc}
<link rel="icon" type="image/png" sizes="32x32" href="/images/favicon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="/images/favicon-192.png">
<link rel="shortcut icon" type="image/png" href="/images/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/images/apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="{esc(SITE["name"])}" href="{SITE["url"]}/feed.xml">
<meta property="og:type" content="website">
<meta property="og:locale" content="en_ZA">
<meta property="og:site_name" content="{esc(SITE["name"])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{og_img}">
<meta property="og:url" content="{SITE["url"]}{canonical}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og_img}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/main.css?v={CSS_HASH}">
{ga4}
{extra}
</head>
<body>
<header class="site-header">
  <div class="site-header__inner">
    <a class="site-logo" href="/">
      <img src="https://static.wixstatic.com/media/4b2909_39f0afa2861e46fdb0af74a03c157a27~mv2.png/v1/crop/x_0,y_519,w_1563,h_525/fill/w_268,h_91,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Pink%20Watercolour%20Flower%20Shop%20Logo.png"
           alt="Mira Accessories" height="50">
    </a>
    <nav class="site-nav" id="site-nav">{nav}</nav>
    <form class="header-search" id="header-search-form" role="search">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      <input type="search" id="header-search-input" placeholder="Search articles..." aria-label="Search">
    </form>
    <a class="shop-btn" href="{SITE["shop_url"]}" target="_blank" rel="noopener">Shop Mira →</a>
    <button class="menu-toggle" id="menu-toggle" aria-label="Toggle menu">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
    </button>
  </div>
</header>
<div class="search-overlay" id="search-overlay" role="dialog" aria-label="Search">
  <button class="search-close" data-search-close aria-label="Close">✕</button>
  <div class="search-box">
    <input class="search-input-large" id="search-input-large" type="search" placeholder="Search articles, tips, products...">
    <div class="search-results" id="search-results"></div>
  </div>
</div>
<main id="main-content">{content}</main>
<footer class="site-footer">
  <div class="site-footer__grid">
    <div>
      <div class="footer-brand__name">Mira Accessories Blog</div>
      <p class="footer-brand__desc">The go-to resource for South African moms on baby and toddler hair care, styling tips, and the best accessories for their little girls.</p>
      <a class="footer-shop-btn" href="{SITE["shop_url"]}" target="_blank" rel="noopener">Shop Mira Accessories →</a>
    </div>
    <div class="footer-col"><div class="footer-col__title">Categories</div>{footer_cats}</div>
    <div class="footer-col">
      <div class="footer-col__title">Shop</div>
      <a href="{SITE["shop_url"]}/category/clip-bows" target="_blank">Pretty Bows</a>
      <a href="{SITE["shop_url"]}/category/cloud-soft-bands" target="_blank">Cloud Soft Bands</a>
      <a href="{SITE["shop_url"]}/category/gift-box-collection" target="_blank">Gift Boxes</a>
      <a href="{SITE["shop_url"]}/category/mom-me" target="_blank">Mom &amp; Me Sets</a>
    </div>
  </div>
  <div class="footer-bottom">
    <span>© {year} Mira Accessories. All rights reserved.</span>
    <span><a href="{SITE["shop_url"]}/privacy-policy" style="color:inherit;">Privacy</a> · <a href="{SITE["shop_url"]}/terms-and-conditions" style="color:inherit;">Terms</a></span>
  </div>
</footer>
<script>{search_idx(posts)}</script>
<script src="/js/search.js?v={JS_HASH}"></script>
</body>
</html>'''


# ── BUILDERS ─────────────────────────────────────────
def build_home(posts, dist):
    feat = next((p for p in posts if p.get('featured')), posts[0] if posts else None)
    rest = [p for p in posts if p is not feat][:9]
    cats = {}
    for p in posts:
        c = p.get('category','')
        if c: cats[c] = cats.get(c,0)+1

    cat_pills = ''.join(f'<a class="cat-pill" href="/category/{slugify(c)}/">{c} <span class="cat-pill__count">{n}</span></a>' for c,n in cats.items())
    cat_grid  = ''.join(f'<a href="/category/{slugify(c)}/" class="cat-grid-item"><span class="cat-grid-name">{c}</span><span class="cat-grid-count">{n} posts →</span></a>' for c,n in cats.items())

    html = f'''
<section class="hero">
  <div class="hero__label">South Africa's Baby Hair Guide</div>
  <h1 class="hero__title">Style guides &amp; tips for <em>SA moms</em></h1>
  <p class="hero__subtitle">Hairstyle ideas, product guides, and expert advice for babies and toddlers across South Africa.</p>
  <form class="hero-search" id="hero-search-form" role="search">
    <input id="hero-search-input" type="search" placeholder="Search hair tips, products, styles..." aria-label="Search">
    <button type="submit">Search</button>
  </form>
</section>
<div class="categories-bar"><div class="categories-bar__inner">
  <a class="cat-pill active" href="/posts/">All posts <span class="cat-pill__count">{len(posts)}</span></a>
  {cat_pills}
</div></div>
<section class="section"><div class="container">
  <div class="section-header"><div><h2 class="section-title">Featured article</h2></div></div>
  {featured_card(feat) if feat else ""}
  <div class="section-header">
    <div><h2 class="section-title">Latest from the blog</h2><p class="section-subtitle">Fresh styling tips and product guides</p></div>
    <a href="/posts/" class="view-all">View all →</a>
  </div>
  <div class="post-grid">{"".join(post_card(p) for p in rest)}</div>
</div></section>
<section class="section--sm" style="background:var(--blush);border-top:1px solid var(--border);border-bottom:1px solid var(--border);">
  <div class="container">
    <div class="section-header"><div><h2 class="section-title">Browse by topic</h2></div></div>
    <div class="cat-grid">{cat_grid}</div>
  </div>
</section>'''

    same_as = [u for u in [SITE.get("instagram"), SITE.get("facebook")] if u]
    org_schema = {"@context":"https://schema.org","@type":"Organization",
        "name":"Mira Accessories","url":SITE["shop_url"],
        "logo":"https://static.wixstatic.com/media/4b2909_39f0afa2861e46fdb0af74a03c157a27~mv2.png",
        "description":"South Africa's premium baby and toddler hair accessories brand.",
        "areaServed":{"@type":"Country","name":"South Africa"},
        "sameAs":same_as}
    website_schema = {"@context":"https://schema.org","@type":"WebSite",
        "name":SITE["name"],"url":SITE["url"],"inLanguage":SITE["locale"],
        "potentialAction":{"@type":"SearchAction",
            "target":f"{SITE['url']}/posts/?q={{search_term_string}}",
            "query-input":"required name=search_term_string"}}
    schema_block = (f'<script type="application/ld+json">{json.dumps(org_schema, ensure_ascii=False)}</script>'
                    f'<script type="application/ld+json">{json.dumps(website_schema, ensure_ascii=False)}</script>')
    dist.mkdir(parents=True, exist_ok=True)
    (dist/'index.html').write_text(
        shell(f"{SITE['name']} — Hair Tips for SA Moms", SITE['description'],
              feat.get('image','') if feat else '', '/', html, posts, extra=schema_block), encoding='utf-8')
    print('  Built: index.html')


def build_about(posts, dist):
    out = dist/'about'
    out.mkdir(parents=True, exist_ok=True)
    person_schema = {"@context":"https://schema.org","@type":"Person",
        "name":AUTHOR["name"],"jobTitle":AUTHOR["title"],
        "description":AUTHOR["bio"],"url":f"{SITE['url']}{AUTHOR['url']}",
        "worksFor":{"@type":"Organization","name":"Mira Accessories","url":SITE["shop_url"]},
        "knowsAbout":["Baby hair care","Toddler hairstyling","South African parenting","Baby hair accessories"]}
    html = f'''<section class="section"><div class="container" style="max-width:720px;">
  <h1 style="font-family:var(--font-serif);font-size:40px;margin-bottom:8px;">About the author</h1>
  <p style="color:var(--mid);margin-bottom:32px;">The person behind every Mira bow.</p>
  <h2 style="font-family:var(--font-serif);font-size:28px;margin-bottom:8px;">{AUTHOR["name"]}</h2>
  <p style="color:var(--mid);margin-bottom:24px;"><em>{AUTHOR["title"]}</em></p>
  <p style="font-size:17px;line-height:1.75;margin-bottom:20px;">{esc(AUTHOR["bio"])}</p>
  <p style="font-size:17px;line-height:1.75;margin-bottom:32px;">Everything on this blog is written with one South African mom in mind at a time — from the first headband in the hospital to the first matching Mom &amp; Me set for a family wedding. If a tip here makes your morning easier, it's done its job.</p>
  <a href="{SITE["shop_url"]}" class="btn-primary" target="_blank" rel="noopener">Visit the Mira shop →</a>
</div></section>'''
    (out/'index.html').write_text(
        shell(f'About {AUTHOR["name"]} — {SITE["name"]}',
              f'{AUTHOR["name"]} — {AUTHOR["title"]}. {AUTHOR["byline_bio"]}',
              '', '/about/', html, posts,
              extra=f'<script type="application/ld+json">{json.dumps(person_schema, ensure_ascii=False)}</script>'),
        encoding='utf-8')
    print('  Built: /about/')


def build_list(posts, dist):
    total = len(posts)
    pages = max(1,(total+PER_PAGE-1)//PER_PAGE)
    pdir  = dist/'posts'
    pdir.mkdir(parents=True, exist_ok=True)
    for n in range(1, pages+1):
        chunk = posts[(n-1)*PER_PAGE:n*PER_PAGE]
        def pu(i): return '/posts/' if i==1 else f'/posts/page/{i}/'
        pager = ''.join(f'<a class="page-btn {"active" if i==n else ""}" href="{pu(i)}">{i}</a>' for i in range(1,pages+1))
        html  = f'''<div class="category-header">
  <h1 class="category-header__title">All blog posts</h1>
  <p class="category-header__count">{total} articles for South African moms</p>
</div>
<section class="section"><div class="container">
  <div class="post-grid">{"".join(post_card(p) for p in chunk)}</div>
  <div class="pagination">
    {'<a class="page-btn" href="'+pu(n-1)+'">←</a>' if n>1 else '<span class="page-btn disabled">←</span>'}
    {pager}
    {'<a class="page-btn" href="'+pu(n+1)+'">→</a>' if n<pages else '<span class="page-btn disabled">→</span>'}
  </div>
</div></section>'''
        out = pdir if n==1 else dist/'posts'/'page'/str(n)
        out.mkdir(parents=True, exist_ok=True)
        (out/'index.html').write_text(
            shell(f'All Posts — {SITE["name"]}', f'Browse all {total} hair care articles for SA moms.',
                  '', pu(n), html, posts), encoding='utf-8')
    print(f'  Built: posts listing ({pages} pages)')


def build_posts(posts, dist):
    for post in posts:
        out = dist/'posts'/post['slug']
        out.mkdir(parents=True, exist_ok=True)
        body    = add_ids(post.get('body',''))
        t       = toc(body)
        recent  = [p for p in posts if p['slug']!=post['slug']][:5]
        tags_h  = ''.join(f'<a class="tag" href="/tags/{slugify(t)}/">{t}</a>' for t in post.get('tags',[]))

        sidebar = f'''<aside class="sidebar">
  {t}
  <div class="sidebar-widget">
    <div class="sidebar-widget__title">Recent articles</div>
    {"".join(sidebar_post(p) for p in recent)}
  </div>
  <div class="sidebar-widget sidebar-widget--cta">
    <div class="sidebar-widget__title">Shop Mira Accessories</div>
    <p style="font-size:13px;color:var(--mid);margin-bottom:14px;">Free delivery on all orders across South Africa.</p>
    <a href="{SITE["shop_url"]}" class="btn-primary" target="_blank" rel="noopener" style="display:block;text-align:center;">Shop now →</a>
  </div>
</aside>'''

        cat      = post.get('category','')
        cat_slug = slugify(cat) if cat else ''
        blog_post_schema = {"@context":"https://schema.org","@type":"BlogPosting",
            "mainEntityOfPage":{"@type":"WebPage","@id":f"{SITE['url']}{post['url']}"},
            "headline":post.get('title',''),"description":post.get('excerpt',''),
            "image":post.get('image',''),"datePublished":post.get('date',''),"dateModified":post.get('date',''),
            "inLanguage":SITE["locale"],
            "author":{"@type":"Person","name":AUTHOR["name"],"jobTitle":AUTHOR["title"],
                      "url":f"{SITE['url']}{AUTHOR['url']}","description":AUTHOR["byline_bio"]},
            "publisher":{"@type":"Organization","name":"Mira Accessories",
                         "url":SITE["shop_url"],
                         "logo":{"@type":"ImageObject","url":"https://static.wixstatic.com/media/4b2909_39f0afa2861e46fdb0af74a03c157a27~mv2.png"}},
            "keywords":', '.join(post.get('keywords',post.get('tags',[])))}
        breadcrumb_schema = {"@context":"https://schema.org","@type":"BreadcrumbList",
            "itemListElement":[
                {"@type":"ListItem","position":1,"name":"Blog","item":f"{SITE['url']}/"},
                {"@type":"ListItem","position":2,"name":cat or "Posts","item":f"{SITE['url']}/category/{cat_slug}/" if cat_slug else f"{SITE['url']}/posts/"},
                {"@type":"ListItem","position":3,"name":post.get('title',''),"item":f"{SITE['url']}{post['url']}"}]}
        # Optional HowTo + FAQ — opt-in via META fields. Generates BOTH visible
        # HTML sections AND matching JSON-LD schema (Google requires the FAQ
        # content to be visible to users for rich-result eligibility).
        #   howto_steps: Step name (timing); Step 2 (timing); ...
        #   faq: Question?||Answer.;Question 2?||Answer 2.
        extra_schemas = []
        howto_visible_html = ''
        faq_visible_html = ''
        howto_raw = (post.get('howto_steps','') or '').strip()
        if howto_raw:
            raw_steps = [x.strip() for x in howto_raw.split(';') if x.strip()]
            steps_schema = [{"@type":"HowToStep","position":i+1,"name":s} for i,s in enumerate(raw_steps)]
            if steps_schema:
                extra_schemas.append({"@context":"https://schema.org","@type":"HowTo",
                    "name":post.get('title',''),
                    "description":post.get('meta_description',post.get('excerpt','')),
                    "image":post.get('image',''),
                    "totalTime":f"PT{len(steps_schema)}M",
                    "step":steps_schema})
                steps_li = ''.join(f'<li>{esc(s)}</li>' for s in raw_steps)
                howto_visible_html = (f'<section class="post-howto" aria-label="Quick steps">'
                                      f'<h2>Quick steps at a glance</h2><ol>{steps_li}</ol></section>')
        faq_raw = (post.get('faq','') or '').strip()
        if faq_raw:
            qa_schema = []
            qa_visible = []
            for pair in [x.strip() for x in faq_raw.split(';') if x.strip()]:
                if '||' not in pair: continue
                q, a = [p.strip() for p in pair.split('||', 1)]
                qa_schema.append({"@type":"Question","name":q,
                    "acceptedAnswer":{"@type":"Answer","text":a}})
                qa_visible.append(f'<details class="faq-item"><summary class="faq-q">{esc(q)}</summary><div class="faq-a">{esc(a)}</div></details>')
            if qa_schema:
                extra_schemas.append({"@context":"https://schema.org","@type":"FAQPage",
                    "mainEntity":qa_schema})
                faq_visible_html = (f'<section class="post-faq" aria-label="Frequently asked questions">'
                                    f'<h2>Frequently asked questions</h2>{"".join(qa_visible)}</section>')
        extras_html = ''.join(
            f'<script type="application/ld+json">{json.dumps(s, ensure_ascii=False)}</script>'
            for s in extra_schemas)
        schema_block = (f'<script type="application/ld+json">{json.dumps(blog_post_schema, ensure_ascii=False)}</script>'
                        f'<script type="application/ld+json">{json.dumps(breadcrumb_schema, ensure_ascii=False)}</script>'
                        + extras_html)

        html = f'''<nav class="breadcrumbs" aria-label="Breadcrumb"><div class="container">
  <a href="/">Home</a> <span>›</span>
  {f'<a href="/category/{cat_slug}/">{cat}</a> <span>›</span>' if cat else ''}
  <span aria-current="page">{esc(post.get("title",""))}</span>
</div></nav>
<header class="post-header">
  <span class="post-category-tag">{post.get("category","")}</span>
  <h1 class="post-header__title">{esc(post.get("title",""))}</h1>
  <div class="post-header__meta">
    <span>By <a href="{AUTHOR["url"]}" rel="author">{AUTHOR["name"]}</a></span><span>{post.get("date","")}</span><span>{post.get("read_time","5 min read")}</span>
  </div>
</header>
<div class="post-hero-image">
  <img src="{wix_img(post.get("image",""), 800, 800)}" srcset="{wix_srcset(post.get("image",""), [400, 600, 800, 1200])}" sizes="(max-width: 800px) 100vw, 800px" alt="{esc(post.get("image_alt", post.get("title","")))}" width="800" height="800" loading="eager">
</div>
<section class="post-body"><div class="container"><div class="post-layout">
  <article>
    <p class="intro">{esc(post.get("excerpt",""))}</p>
    {body}
    {howto_visible_html}
    {faq_visible_html}
    <hr class="divider">
    <div class="tag-cloud">{tags_h}</div>
  </article>
  {sidebar}
</div></div></section>
{related_section(post, posts)}'''

        # Author bio — boxed card with monogram avatar (initials), styled like
        # a polished "About the author" block (Cup of Jo / Honestly Modern style).
        initials = ''.join(p[0] for p in AUTHOR["name"].split() if p)[:2].upper()
        author_card = f'''<section class="author-card"><div class="container">
  <div class="author-card__inner">
    <div class="author-card__avatar" aria-hidden="true">{initials}</div>
    <div class="author-card__text">
      <div class="author-card__label">Written by</div>
      <div class="author-card__name"><a href="{AUTHOR["url"]}">{AUTHOR["name"]}</a></div>
      <p class="author-card__role">{esc(AUTHOR["title"])}</p>
      <p class="author-card__bio">{esc(AUTHOR["byline_bio"])}</p>
      <a class="author-card__more" href="{AUTHOR["url"]}">More about Shaveta →</a>
    </div>
  </div>
</div></section>'''
        (out/'index.html').write_text(
            shell(f'{post.get("title","")} | {SITE["name"]}',
                  post.get('meta_description', post.get('excerpt','')),
                  post.get('image',''), post['url'], html + author_card, posts,
                  extra=schema_block),
            encoding='utf-8')
    print(f'  Built: {len(posts)} post pages')


def build_cats(posts, dist):
    cats = {}
    for p in posts:
        c = p.get('category','')
        if c: cats.setdefault(c,[]).append(p)
    for name, cps in cats.items():
        out = dist/'category'/slugify(name)
        out.mkdir(parents=True, exist_ok=True)
        html = f'''<div class="category-header">
  <h1 class="category-header__title">{name}</h1>
  <p class="category-header__count">{len(cps)} articles</p>
</div>
<section class="section"><div class="container"><div class="post-grid">{"".join(post_card(p) for p in cps)}</div></div></section>'''
        (out/'index.html').write_text(
            shell(f'{name} — {SITE["name"]}', f'Browse {len(cps)} articles about {name} for SA moms.',
                  cps[0].get('image','') if cps else '', f'/category/{slugify(name)}/', html, posts),
            encoding='utf-8')
    print(f'  Built: {len(cats)} category pages')


def build_tags(posts, dist):
    tags = {}
    for p in posts:
        for t in p.get('tags',[]): tags.setdefault(t,[]).append(p)
    for name, tps in tags.items():
        out = dist/'tags'/slugify(name)
        out.mkdir(parents=True, exist_ok=True)
        html = f'''<div class="category-header">
  <h1 class="category-header__title">#{name}</h1>
  <p class="category-header__count">{len(tps)} articles</p>
</div>
<section class="section"><div class="container"><div class="post-grid">{"".join(post_card(p) for p in tps)}</div></div></section>'''
        (out/'index.html').write_text(
            shell(f'#{name} — {SITE["name"]}', f'All articles tagged {name}.',
                  tps[0].get('image','') if tps else '', f'/tags/{slugify(name)}/', html, posts),
            encoding='utf-8')
    print(f'  Built: {len(tags)} tag pages')


def build_extras(posts, dist):
    urls = [f'  <url><loc>{SITE["url"]}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>',
            f'  <url><loc>{SITE["url"]}/posts/</loc><changefreq>daily</changefreq><priority>0.9</priority></url>',
            f'  <url><loc>{SITE["url"]}/about/</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>']
    for p in posts:
        img = p.get('image','')
        img_block = (f'\n    <image:image><image:loc>{esc(img)}</image:loc>'
                     f'<image:title>{esc(p.get("title",""))}</image:title>'
                     f'<image:caption>{esc(p.get("image_alt", p.get("title","")))}</image:caption></image:image>') if img else ''
        urls.append(f'  <url><loc>{SITE["url"]}{p["url"]}</loc><lastmod>{p.get("date","")}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority>{img_block}</url>')
    (dist/'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        +'\n'.join(urls)+'\n</urlset>', encoding='utf-8')
    (dist/'robots.txt').write_text(
        f'User-agent: *\nAllow: /\n\n'
        f'Sitemap: {SITE["url"]}/sitemap.xml\n'
        f'Host: {SITE["url"].replace("https://","")}\n', encoding='utf-8')
    (dist/'CNAME').write_text('blog.miraaccessories.co.za',encoding='utf-8')
    err = '<div style="text-align:center;padding:100px 24px;"><div style="font-family:var(--font-serif);font-size:80px;color:var(--border)">404</div><h1 style="font-family:var(--font-serif);font-size:32px;margin:16px 0 12px">Page not found</h1><p style="color:var(--mid);margin-bottom:32px">This article has moved or doesn\'t exist.</p><a href="/" class="btn-primary">Back to home →</a></div>'
    (dist/'404.html').write_text(shell(f'404 — {SITE["name"]}','Page not found.','','/404/',err,posts),encoding='utf-8')
    print('  Built: sitemap (with images), robots.txt, CNAME, 404')


def build_feed(posts, dist):
    items = []
    for p in posts[:20]:
        pub = p.get('date','')
        try:
            pub_rfc = datetime.strptime(pub, "%Y-%m-%d").strftime("%a, %d %b %Y 09:00:00 +0200")
        except Exception:
            pub_rfc = ""
        items.append(
            f'    <item>\n'
            f'      <title>{esc(p.get("title",""))}</title>\n'
            f'      <link>{SITE["url"]}{p["url"]}</link>\n'
            f'      <guid isPermaLink="true">{SITE["url"]}{p["url"]}</guid>\n'
            f'      <pubDate>{pub_rfc}</pubDate>\n'
            f'      <category>{esc(p.get("category",""))}</category>\n'
            f'      <dc:creator>{esc(AUTHOR["name"])}</dc:creator>\n'
            f'      <description>{esc(p.get("excerpt",""))}</description>\n'
            f'    </item>'
        )
    now = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0200")
    rss = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:atom="http://www.w3.org/2005/Atom">\n'
           '  <channel>\n'
           f'    <title>{esc(SITE["name"])}</title>\n'
           f'    <link>{SITE["url"]}</link>\n'
           f'    <description>{esc(SITE["description"])}</description>\n'
           f'    <language>en-ZA</language>\n'
           f'    <lastBuildDate>{now}</lastBuildDate>\n'
           f'    <atom:link href="{SITE["url"]}/feed.xml" rel="self" type="application/rss+xml"/>\n'
           + '\n'.join(items) + '\n'
           '  </channel>\n'
           '</rss>\n')
    (dist/'feed.xml').write_text(rss, encoding='utf-8')
    print('  Built: feed.xml (RSS)')


def build_drafts(drafts, all_posts, dist):
    """Render drafts into dist/posts-drafts/ with a visible DRAFT banner and noindex meta.
    Uses real posts for related-posts, so drafts don't pollute each other's sidebar.
    Never touches dist/posts/ — drafts can never accidentally be deployed."""
    if not drafts:
        return
    banner = ('<div style="position:sticky;top:0;z-index:999;background:#b33;color:#fff;'
              'text-align:center;padding:10px 16px;font-weight:600;font-size:14px;'
              'letter-spacing:0.5px;">⚠ DRAFT PREVIEW — not published, not indexed, local only</div>')
    noindex = '<meta name="robots" content="noindex, nofollow, noarchive">'
    for post in drafts:
        out = dist/'posts-drafts'/post['slug']
        out.mkdir(parents=True, exist_ok=True)
        body     = add_ids(post.get('body',''))
        t        = toc(body)
        recent   = [p for p in all_posts if p['slug']!=post['slug']][:5]
        tags_h   = ''.join(f'<a class="tag" href="/tags/{slugify(tg)}/">{tg}</a>' for tg in post.get('tags',[]))
        cat      = post.get('category','')
        cat_slug = slugify(cat) if cat else ''
        sidebar = f'''<aside class="sidebar">
  {t}
  <div class="sidebar-widget">
    <div class="sidebar-widget__title">Recent articles</div>
    {"".join(sidebar_post(p) for p in recent)}
  </div>
</aside>'''
        html = f'''{banner}
<nav class="breadcrumbs" aria-label="Breadcrumb"><div class="container">
  <a href="/">Home</a> <span>›</span>
  {f'<a href="/category/{cat_slug}/">{cat}</a> <span>›</span>' if cat else ''}
  <span aria-current="page">{esc(post.get("title",""))}</span>
</div></nav>
<header class="post-header">
  <span class="post-category-tag">{post.get("category","")}</span>
  <h1 class="post-header__title">{esc(post.get("title",""))}</h1>
  <div class="post-header__meta">
    <span>By <a href="{AUTHOR["url"]}" rel="author">{AUTHOR["name"]}</a></span><span>{post.get("date","")}</span><span>{post.get("read_time","5 min read")}</span>
  </div>
</header>
<div class="post-hero-image">
  <img src="{wix_img(post.get("image",""), 800, 800)}" srcset="{wix_srcset(post.get("image",""), [400, 600, 800, 1200])}" sizes="(max-width: 800px) 100vw, 800px" alt="{esc(post.get("image_alt", post.get("title","")))}" width="800" height="800" loading="eager">
</div>
<section class="post-body"><div class="container"><div class="post-layout">
  <article>
    <p class="intro">{esc(post.get("excerpt",""))}</p>
    {body}
    <hr class="divider">
    <div class="tag-cloud">{tags_h}</div>
  </article>
  {sidebar}
</div></div></section>'''
        (out/'index.html').write_text(
            shell(f'[DRAFT] {post.get("title","")} | {SITE["name"]}',
                  post.get('meta_description', post.get('excerpt','')),
                  post.get('image',''), f'/posts-drafts/{post["slug"]}/', html, all_posts,
                  extra=noindex),
            encoding='utf-8')

    # Draft index page
    idx_cards = ''.join(post_card(p) for p in drafts)
    idx_html = f'''{banner}
<div class="category-header">
  <h1 class="category-header__title">Draft previews</h1>
  <p class="category-header__count">{len(drafts)} local-only drafts · not published · not indexed</p>
</div>
<section class="section"><div class="container">
  <div class="post-grid">{idx_cards}</div>
</div></section>'''
    (dist/'posts-drafts').mkdir(parents=True, exist_ok=True)
    (dist/'posts-drafts'/'index.html').write_text(
        shell(f'[DRAFT] Drafts — {SITE["name"]}', 'Local draft previews.',
              '', '/posts-drafts/', idx_html, all_posts, extra=noindex),
        encoding='utf-8')
    print(f'  Built: {len(drafts)} draft preview(s) → /posts-drafts/')


# ── MAIN ─────────────────────────────────────────────
def build():
    print(f'\n🌸 Mira Blog\n{"─"*36}')
    if DIST_DIR.exists(): shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)
    shutil.copytree(STATIC_DIR, DIST_DIR, dirs_exist_ok=True)
    global CSS_HASH, JS_HASH
    CSS_HASH = _file_hash(STATIC_DIR / "css" / "main.css")
    JS_HASH  = _file_hash(STATIC_DIR / "js" / "search.js")
    print(f'  Copied static assets (css {CSS_HASH}, js {JS_HASH})')
    posts = load_posts()
    print(f'  Loaded {len(posts)} posts')
    if not posts:
        print('  ⚠  Add HTML files to /posts/ to get started')
    build_home(posts, DIST_DIR)
    build_list(posts, DIST_DIR)
    build_posts(posts, DIST_DIR)
    build_cats(posts, DIST_DIR)
    build_tags(posts, DIST_DIR)
    build_about(posts, DIST_DIR)
    build_feed(posts, DIST_DIR)
    build_extras(posts, DIST_DIR)
    if "--drafts" in sys.argv:
        drafts = load_posts(POSTS_DIR/"drafts", url_prefix="/posts-drafts/")
        build_drafts(drafts, posts, DIST_DIR)
    total = sum(1 for _ in DIST_DIR.rglob('*.html'))
    print(f'\n✓ {total} HTML pages → dist/\n')

if __name__ == '__main__':
    build()
