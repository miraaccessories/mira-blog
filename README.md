# Mira Accessories Blog

Static blog site for [blog.miraaccessories.co.za](https://blog.miraaccessories.co.za)

Built with pure Python — no Node, no npm, no frameworks. Just HTML + CSS output.

---

## Project structure

```
mira-blog/
├── posts/              ← Blog posts as JSON files (one per post)
├── static/
│   ├── css/main.css    ← All styles
│   └── js/search.js    ← Client-side search
├── scripts/
│   └── build.py        ← Static site generator
├── dist/               ← Generated output (never commit this)
└── .github/
    └── workflows/
        └── deploy.yml  ← Auto-deploy to GitHub Pages
```

---

## Writing a new blog post

Create a new JSON file in `/posts/` named `YYYY-MM-DD-your-slug.json`:

```json
{
  "title": "Your Blog Post Title",
  "date": "2025-04-20",
  "category": "School Hair",
  "read_time": "6 min read",
  "image": "https://your-image-url.jpg",
  "image_alt": "Descriptive alt text for SEO",
  "excerpt": "150 characters describing the post — shown in cards and meta description fallback.",
  "meta_description": "155-character SEO meta description with focus keyword.",
  "keywords": ["keyword 1", "keyword 2", "keyword 3"],
  "tags": ["School Hair", "Toddler Hairstyles", "South Africa"],
  "content": "<p>Your full HTML blog post content here...</p>"
}
```

### Available categories
- `School Hair`
- `Baby Care`
- `Gift Ideas`
- `Mom & Baby`
- `Photoshoots`

### HTML components available in content

**Product card (large):**
```html
<a class="product-card" href="PRODUCT_URL" target="_blank" rel="noopener">
  <img src="IMAGE_URL" alt="ALT TEXT" width="110" height="110">
  <div class="product-card__info">
    <div class="product-card__label">Mira Accessories · Category</div>
    <div class="product-card__name">Product Name</div>
    <div class="product-card__desc">Short description.</div>
    <div class="product-card__price">R199</div>
    <a class="btn-shop" href="PRODUCT_URL" target="_blank">Shop now →</a>
  </div>
</a>
```

**Product grid (2-up):**
```html
<div class="product-grid">
  <a class="product-grid-card" href="URL" target="_blank">
    <img src="IMAGE" alt="ALT" width="300" height="300">
    <div class="product-grid-card__info">
      <div class="product-grid-card__name">Name</div>
      <div class="product-grid-card__price">R149</div>
      <span class="btn-outline-sm">Shop →</span>
    </div>
  </a>
</div>
```

**Pull quote:**
```html
<div class="pull-quote"><p>Your quote here.</p></div>
```

**Tip box:**
```html
<div class="tip-box">
  <div class="tip-label">SA Mom Tip</div>
  <p>Your tip here.</p>
</div>
```

**Checklist:**
```html
<ul class="styled-list checked">
  <li>Item one</li>
  <li>Item two</li>
</ul>
```

**CTA block:**
```html
<div class="cta-block">
  <h3>Shop heading</h3>
  <p>Supporting text.</p>
  <a class="btn-primary" href="URL" target="_blank">Shop now →</a>
</div>
```

---

## Building locally

```bash
# Requires Python 3.8+
python3 scripts/build.py
```

Output goes to `dist/`. Open `dist/index.html` in a browser to preview.

---

## Deploying to GitHub Pages

### First time setup

1. Push this repo to GitHub (any name, e.g. `mira-blog`)
2. Go to **Settings → Pages** in your GitHub repo
3. Under **Source**, select **GitHub Actions**
4. Push to `main` — the workflow builds and deploys automatically

### Setting up the custom domain

**In GitHub:**
1. Go to **Settings → Pages**
2. Under **Custom domain**, enter: `blog.miraaccessories.co.za`
3. Click Save

**In your domain registrar (DNS settings):**

Add these DNS records for `miraaccessories.co.za`:

| Type | Name | Value |
|------|------|-------|
| CNAME | `blog` | `YOUR-GITHUB-USERNAME.github.io` |

Replace `YOUR-GITHUB-USERNAME` with your actual GitHub username.

**Wait for DNS propagation** — usually 10 minutes to 2 hours.

After DNS is set, go back to GitHub Settings → Pages and tick **Enforce HTTPS**.

Your blog will be live at `https://blog.miraaccessories.co.za`

---

## Workflow

Every time you push to `main`:
1. GitHub Actions runs `python3 scripts/build.py`
2. The `dist/` output is deployed to GitHub Pages
3. Your site updates within ~2 minutes

---

## Product image URLs (copy-paste ready)

```
Rosy Bloom Rose Clip (R199):
https://static.wixstatic.com/media/c0dda5_1317a69f23bd45beb4635f5829f88cb8~mv2.jpg/v1/fill/w_600,h_600,al_c,q_80/c0dda5_1317a69f23bd45beb4635f5829f88cb8~mv2.jpg

Lilac Whisper Bow Clip (R189):
https://static.wixstatic.com/media/c0dda5_039eb1f89dd64ca1bdd52eeb6808581a~mv2.jpg/v1/fill/w_600,h_600,al_c,q_80/c0dda5_039eb1f89dd64ca1bdd52eeb6808581a~mv2.jpg

Sage Whisper Bow Clip (R129):
https://static.wixstatic.com/media/c0dda5_eef6e6aede5e4e22b2f760214d0ae98c~mv2.jpg/v1/fill/w_600,h_600,al_c,q_80/c0dda5_eef6e6aede5e4e22b2f760214d0ae98c~mv2.jpg

Pearl Whisper Bow (R149):
https://static.wixstatic.com/media/c0dda5_6c5d6948dc1946f18ba0e31b1ba8472e~mv2.jpg/v1/fill/w_600,h_600,al_c,q_80/c0dda5_6c5d6948dc1946f18ba0e31b1ba8472e~mv2.jpg

Lilac Linen Bow (R159):
https://static.wixstatic.com/media/c0dda5_0a07c5ef972d4414bc9c6a3a760e871c~mv2.jpg/v1/fill/w_600,h_600,al_c,q_80/c0dda5_0a07c5ef972d4414bc9c6a3a760e871c~mv2.jpg

Blush Pearl Petal Clips (R239):
https://static.wixstatic.com/media/c0dda5_7bd061ce6b3d4e6e92aedce8a1d907d8~mv2.jpg/v1/fill/w_600,h_600,al_c,q_80/c0dda5_7bd061ce6b3d4e6e92aedce8a1d907d8~mv2.jpg

Peach Velvet Mom & Me Set (R399):
https://static.wixstatic.com/media/c0dda5_d60aa7ebf8fb46c3b154c191fd1c6e42~mv2.jpg/v1/fill/w_600,h_600,al_c,q_80/c0dda5_d60aa7ebf8fb46c3b154c191fd1c6e42~mv2.jpg

Garden Fairy Gift Box (R549):
https://static.wixstatic.com/media/c0dda5_086167d3b16240439d9614bc28ff741a~mv2.jpg/v1/fill/w_600,h_600,al_c,q_80/c0dda5_086167d3b16240439d9614bc28ff741a~mv2.jpg

Blush Bloom Gift Box (R399):
https://static.wixstatic.com/media/c0dda5_1b6fa39022d049618af9955bd92f1e35~mv2.jpg/v1/fill/w_600,h_600,al_c,q_80/c0dda5_1b6fa39022d049618af9955bd92f1e35~mv2.jpg
```
