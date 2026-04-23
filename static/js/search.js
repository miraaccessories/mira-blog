// Mira Blog — Client-side search
// Search index is built at compile time and embedded in the page

(function() {
  'use strict';

  let searchIndex = [];
  let searchOverlay, searchInput, searchResults;

  function init() {
    searchOverlay = document.getElementById('search-overlay');
    searchInput = document.getElementById('search-input-large');
    searchResults = document.getElementById('search-results');

    // Load index — embedded as window.SEARCH_INDEX by build script
    if (window.SEARCH_INDEX) {
      searchIndex = window.SEARCH_INDEX;
    }

    // Wire up triggers
    document.querySelectorAll('[data-search-open]').forEach(el => {
      el.addEventListener('click', openSearch);
    });

    document.querySelectorAll('[data-search-close]').forEach(el => {
      el.addEventListener('click', closeSearch);
    });

    // Header search form
    const headerSearch = document.getElementById('header-search-form');
    if (headerSearch) {
      headerSearch.addEventListener('submit', function(e) {
        e.preventDefault();
        const q = document.getElementById('header-search-input').value.trim();
        if (q) openSearch(q);
      });
    }

    // Hero search form
    const heroSearch = document.getElementById('hero-search-form');
    if (heroSearch) {
      heroSearch.addEventListener('submit', function(e) {
        e.preventDefault();
        const q = document.getElementById('hero-search-input').value.trim();
        if (q) openSearch(q);
      });
    }

    if (searchOverlay) {
      searchOverlay.addEventListener('click', function(e) {
        if (e.target === searchOverlay) closeSearch();
      });
    }

    if (searchInput) {
      searchInput.addEventListener('input', debounce(function() {
        runSearch(searchInput.value);
      }, 200));
    }

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') closeSearch();
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        openSearch();
      }
    });
  }

  function openSearch(query) {
    if (!searchOverlay) return;
    searchOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
    setTimeout(() => {
      if (searchInput) {
        searchInput.focus();
        if (typeof query === 'string' && query) {
          searchInput.value = query;
          runSearch(query);
        }
      }
    }, 50);
  }

  function closeSearch() {
    if (!searchOverlay) return;
    searchOverlay.classList.remove('active');
    document.body.style.overflow = '';
    if (searchInput) searchInput.value = '';
    if (searchResults) searchResults.innerHTML = '';
  }

  function runSearch(query) {
    if (!query || query.length < 2) {
      searchResults.innerHTML = '';
      return;
    }

    const q = query.toLowerCase().trim();
    const terms = q.split(/\s+/);

    const scored = searchIndex.map(post => {
      let score = 0;
      const title = (post.title || '').toLowerCase();
      const excerpt = (post.excerpt || '').toLowerCase();
      const tags = (post.tags || []).join(' ').toLowerCase();
      const category = (post.category || '').toLowerCase();
      const content = (post.content || '').toLowerCase();

      terms.forEach(term => {
        if (title.includes(term)) score += 10;
        if (category.includes(term)) score += 6;
        if (tags.includes(term)) score += 5;
        if (excerpt.includes(term)) score += 3;
        if (content.includes(term)) score += 1;
      });

      // Bonus for exact phrase match
      if (title.includes(q)) score += 15;
      if (excerpt.includes(q)) score += 5;

      return { post, score };
    }).filter(r => r.score > 0).sort((a, b) => b.score - a.score);

    renderResults(scored.slice(0, 8), query);
  }

  function renderResults(results, query) {
    if (!searchResults) return;

    if (results.length === 0) {
      searchResults.innerHTML = `<div class="search-no-results">No posts found for "<strong>${escHtml(query)}</strong>"<br><span style="font-size:13px;opacity:0.6;">Try different keywords</span></div>`;
      return;
    }

    searchResults.innerHTML = results.map(({ post }) => `
      <a class="search-result-item" href="${post.url}">
        <img class="search-result-img" src="${post.image || ''}" alt="${escHtml(post.title)}" onerror="this.style.background='#f5e8eb';this.src=''">
        <div>
          <div class="search-result-title">${highlight(post.title, query)}</div>
          <div class="search-result-excerpt">${highlight(post.excerpt, query)}</div>
          <div style="font-size:11px;color:var(--rose);margin-top:4px;">${escHtml(post.category || '')}</div>
        </div>
      </a>
    `).join('');
  }

  function highlight(text, query) {
    if (!text) return '';
    const escaped = escHtml(text);
    const terms = query.toLowerCase().split(/\s+/).filter(t => t.length > 1);
    let result = escaped;
    terms.forEach(term => {
      const re = new RegExp(`(${escRegex(term)})`, 'gi');
      result = result.replace(re, '<mark style="background:#f5e8eb;color:#8b4a57;border-radius:3px;padding:0 2px;">$1</mark>');
    });
    return result;
  }

  function escHtml(str) {
    return String(str || '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  function escRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function debounce(fn, delay) {
    let timer;
    return function(...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  // Mobile menu
  function initMobileMenu() {
    const toggle = document.getElementById('menu-toggle');
    const nav = document.getElementById('site-nav');
    if (toggle && nav) {
      toggle.addEventListener('click', () => {
        nav.classList.toggle('open');
      });
    }
  }

  // Active nav
  function setActiveNav() {
    const current = window.location.pathname;
    document.querySelectorAll('.site-nav a').forEach(a => {
      const href = a.getAttribute('href');
      if (href && current.startsWith(href) && href !== '/') {
        a.classList.add('active');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    init();
    initMobileMenu();
    setActiveNav();
  });

})();
