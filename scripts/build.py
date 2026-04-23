#!/usr/bin/env python3
"""
Mira Blog — Static Site Generator
Post format: /posts/YYYY-MM-DD-slug.html
Each post has a META comment block at the top, then raw HTML body.
Run: python3 scripts/build.py
Output: dist/
"""

import json, re, shutil
from datetime import datetime
from pathlib import Path

SITE = {
    "name":        "Mira Accessories Blog",
    "url":         "https://blog.miraaccessories.co.za",
    "shop_url":    "https://www.miraaccessories.co.za",
    "description": "Expert advice on baby and toddler hair care, styling tips, and the best hair accessories for South African moms.",
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


# ── POST LOADER ─────────────────────────────────────
def load_posts():
    posts = []
    for f in POSTS_DIR.glob("*.html"):
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
        body = re.sub(r'<!--META\n.*?-->', '', raw, flags=re.DOTALL).strip()
        excerpt = meta.get('excerpt', re.sub(r'<[^>]+>','',body)[:160].strip()+'...')
        posts.append({**meta, 'slug': f.stem, 'url': f'/posts/{f.stem}/',
                      'body': body, 'excerpt': excerpt})
    posts.sort(key=lambda p: p.get('date',''), reverse=True)
    return posts


# ── COMPONENTS ──────────────────────────────────────
def post_card(p):
    return f'''<a class="post-card" href="{p['url']}">
  <div class="post-card__image-wrap">
    <img class="post-card__image" src="{p.get('image','')}" alt="{esc(p.get('image_alt', p.get('title','')))}" loading="lazy" width="400" height="250">
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
  <img class="featured-post__image" src="{p.get('image','')}" alt="{esc(p.get('image_alt', p.get('title','')))}" width="600" height="450" loading="eager">
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
  <img src="{p.get('image','')}" alt="{esc(p.get('title',''))}" loading="lazy" width="52" height="52">
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
        ('Mom &amp; Baby','/category/mom-and-baby/'),('Photoshoots','/category/photoshoots/'),
    ])
    footer_cats = ''.join(f'<a href="/category/{slugify(c)}/">{c}</a>' for c in cats)
    year = datetime.now().year

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{SITE["url"]}{canonical}">
<link rel="icon" type="image/png" sizes="32x32" href="/images/favicon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="/images/favicon-192.png">
<link rel="shortcut icon" type="image/png" href="/images/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/images/apple-touch-icon.png">
<meta property="og:type" content="website">
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
<link rel="stylesheet" href="/css/main.css">
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
    <input class="search-input-large" id="search-input-large" type="search" placeholder="Search articles, tips, products..." autofocus>
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
<script src="/js/search.js"></script>
</body>
</html>'''


# ── BUILDERS ─────────────────────────────────────────
def build_home(posts, dist):
    feat = posts[0] if posts else None
    rest = posts[1:10]
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

    dist.mkdir(parents=True, exist_ok=True)
    (dist/'index.html').write_text(
        shell(f"{SITE['name']} — Hair Tips for SA Moms", SITE['description'],
              feat.get('image','') if feat else '', '/', html, posts), encoding='utf-8')
    print('  Built: index.html')


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

        schema = json.dumps({"@context":"https://schema.org","@type":"BlogPosting",
            "headline":post.get('title',''),"description":post.get('excerpt',''),
            "image":post.get('image',''),"datePublished":post.get('date',''),
            "author":{"@type":"Organization","name":"Mira Accessories"},
            "publisher":{"@type":"Organization","name":"Mira Accessories"},
            "keywords":', '.join(post.get('keywords',post.get('tags',[])))})

        html = f'''<header class="post-header">
  <span class="post-category-tag">{post.get("category","")}</span>
  <h1 class="post-header__title">{esc(post.get("title",""))}</h1>
  <div class="post-header__meta">
    <span>Mira Accessories</span><span>{post.get("date","")}</span><span>{post.get("read_time","5 min read")}</span>
  </div>
</header>
<div class="post-hero-image">
  <img src="{post.get("image","")}" alt="{esc(post.get("image_alt", post.get("title","")))}" width="900" height="506" loading="eager">
</div>
<section class="post-body"><div class="container"><div class="post-layout">
  <article>
    <p class="intro">{esc(post.get("excerpt",""))}</p>
    {body}
    <hr class="divider">
    <div class="tag-cloud">{tags_h}</div>
  </article>
  {sidebar}
</div></div></section>
{related_section(post, posts)}'''

        (out/'index.html').write_text(
            shell(f'{post.get("title","")} | {SITE["name"]}',
                  post.get('meta_description', post.get('excerpt','')),
                  post.get('image',''), post['url'], html, posts,
                  extra=f'<script type="application/ld+json">{schema}</script>'),
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
            f'  <url><loc>{SITE["url"]}/posts/</loc><changefreq>daily</changefreq><priority>0.9</priority></url>']
    for p in posts:
        urls.append(f'  <url><loc>{SITE["url"]}{p["url"]}</loc><lastmod>{p.get("date","")}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>')
    (dist/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+'\n'.join(urls)+'\n</urlset>',encoding='utf-8')
    (dist/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {SITE["url"]}/sitemap.xml\n',encoding='utf-8')
    (dist/'CNAME').write_text('blog.miraaccessories.co.za',encoding='utf-8')
    err = '<div style="text-align:center;padding:100px 24px;"><div style="font-family:var(--font-serif);font-size:80px;color:var(--border)">404</div><h1 style="font-family:var(--font-serif);font-size:32px;margin:16px 0 12px">Page not found</h1><p style="color:var(--mid);margin-bottom:32px">This article has moved or doesn\'t exist.</p><a href="/" class="btn-primary">Back to home →</a></div>'
    (dist/'404.html').write_text(shell(f'404 — {SITE["name"]}','Page not found.','','/404/',err,posts),encoding='utf-8')
    print('  Built: sitemap, robots.txt, CNAME, 404')


# ── MAIN ─────────────────────────────────────────────
def build():
    print(f'\n🌸 Mira Blog\n{"─"*36}')
    if DIST_DIR.exists(): shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)
    shutil.copytree(STATIC_DIR, DIST_DIR, dirs_exist_ok=True)
    print('  Copied static assets')
    posts = load_posts()
    print(f'  Loaded {len(posts)} posts')
    if not posts:
        print('  ⚠  Add HTML files to /posts/ to get started')
    build_home(posts, DIST_DIR)
    build_list(posts, DIST_DIR)
    build_posts(posts, DIST_DIR)
    build_cats(posts, DIST_DIR)
    build_tags(posts, DIST_DIR)
    build_extras(posts, DIST_DIR)
    total = sum(1 for _ in DIST_DIR.rglob('*.html'))
    print(f'\n✓ {total} HTML pages → dist/\n')

if __name__ == '__main__':
    build()
