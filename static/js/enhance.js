// Reading progress bar — updates the .reading-progress element width to
// reflect how far the reader has scrolled through the article. Only runs
// when an article is present.
(function () {
  var bar = document.getElementById('reading-progress');
  var article = document.querySelector('article');
  if (!bar || !article) return;

  function update() {
    var rect = article.getBoundingClientRect();
    var total = article.offsetHeight - window.innerHeight;
    if (total <= 0) { bar.style.width = '100%'; return; }
    var scrolled = Math.min(Math.max(-rect.top, 0), total);
    bar.style.width = ((scrolled / total) * 100).toFixed(2) + '%';
  }

  window.addEventListener('scroll', update, { passive: true });
  window.addEventListener('resize', update, { passive: true });
  update();
})();

// Copy-link share button — works on every page that has a [data-copy-link]
// element. Falls back gracefully if clipboard API isn't available.
(function () {
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-copy-link]');
    if (!btn) return;
    e.preventDefault();
    var url = btn.getAttribute('data-copy-link');
    var done = function () {
      var original = btn.textContent;
      btn.textContent = 'Link copied ✓';
      setTimeout(function () { btn.textContent = original; }, 1800);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(done, function () {
        window.prompt('Copy this link:', url);
      });
    } else {
      window.prompt('Copy this link:', url);
    }
  });
})();
