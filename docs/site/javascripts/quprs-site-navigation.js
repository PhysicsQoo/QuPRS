/* Progressive enhancement of the native Zensical/Material header.
 * If upstream markup changes, the native search/version/source header stays intact.
 * Project links remain available in the configured documentation navigation.
 */
(() => {
  "use strict";

  function enhanceHeader() {
    const header = document.querySelector(
      'header[data-md-component="header"] > nav.md-header__inner'
    );
    if (!header || header.querySelector("[data-quprs-site-links]")) return;
    const searchAction = header.querySelector('label[for="__search"]');
    if (!searchAction) return;

    const path = window.location.pathname;
    const version = path.match(
      /^\/QuPRS\/docs\/(dev|v[0-9]+\.[0-9]+\.[0-9]+(?:-test)?)\//
    );
    const preview = path.match(/^\/QuPRS\/pr-preview\/pr-[0-9]+\//);
    const base = preview
      ? preview[0]
      : version
        ? "/QuPRS/docs/" + version[1] + "/"
        : "/QuPRS/docs/stable/";

    const links = document.createElement("div");
    links.className = "quprs-site-links";
    links.setAttribute("role", "navigation");
    links.setAttribute("aria-label", "QuPRS site navigation");
    links.setAttribute("data-quprs-site-links", "");

    for (const [href, label] of [
      ["/QuPRS/", "Home"],
      ["/QuPRS/playground/", "Playground"],
      [base + "rust-api/quprs/", "Rust API"],
      ["https://github.com/PhysicsQoo/QuPRS/releases", "Releases"]
    ]) {
      const link = document.createElement("a");
      link.href = href;
      link.textContent = label;
      links.append(link);
    }
    header.insertBefore(links, searchAction);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhanceHeader, { once: true });
  } else {
    enhanceHeader();
  }
})();
