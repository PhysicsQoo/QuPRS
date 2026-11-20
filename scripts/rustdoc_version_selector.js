/* QuPRS Rustdoc version navigation. Native rustdoc markup and search stay intact. */
(() => {
  "use strict";
  const script = document.currentScript;
  if (!script) return;

  const src = new URL(script.src, document.baseURI);
  const source = src.pathname.match(
    /^\/QuPRS\/docs\/(dev|v[0-9]+\.[0-9]+\.[0-9]+(?:-test)?)\/rust-api\/quprs-versions\.js$/
  );
  const preview = /^\/QuPRS\/pr-preview\/pr-[0-9]+\/rust-api\/quprs-versions\.js$/.test(src.pathname);
  if (!source && !preview) return;

  const docsPrefix = "/QuPRS/docs/";
  const validVersion = value => /^(dev|v[0-9]+\.[0-9]+\.[0-9]+(?:-test)?)$/.test(value);
  const current = source ? source[1] : null;

  function render() {
    if (document.querySelector("nav[data-quprs-version-selector]")) return;
    // Rustdoc uses body.rustdoc as a horizontal flex layout on desktop.
    // A body-level navigation sibling becomes an unwanted column. Keep the
    // native sidebar/topbar untouched and enhance only the content column.
    const main = document.querySelector("main");
    if (!main) return;
    const bar = document.createElement("nav");
    bar.className = "quprs-version-switcher";
    bar.setAttribute("aria-label", "QuPRS Rust API documentation version");
    bar.setAttribute("data-quprs-version-selector", "");

    const label = document.createElement("label");
    label.textContent = "Rust API version";
    const select = document.createElement("select");
    select.setAttribute("aria-label", "Rust API version");
    select.disabled = true;
    label.append(" ", select);
    bar.append(label);

    const links = document.createElement("span");
    links.className = "quprs-version-links";
    for (const [href, title] of [
      ["/QuPRS/", "Home"],
      ["/QuPRS/playground/", "Playground"],
      [docsPrefix, "Documentation"],
      ["https://github.com/PhysicsQoo/QuPRS", "GitHub"],
      ["https://github.com/PhysicsQoo/QuPRS/releases", "Releases"]
    ]) {
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.textContent = title;
      links.append(anchor);
    }
    bar.append(links);

    main.insertBefore(bar, main.firstChild);

    function option(value, title, selected = false) {
      const item = new Option(title, value, selected, selected);
      select.add(item);
    }
    if (preview) {
      // An isolated PR preview contains only its own subtree, not the live
      // /docs/versions.json manifest. Never request a missing resource from
      // the preview server; users can return to the published docs via link.
      option("preview", "PR preview", true);
      return;
    }
    option("loading", "Loading versions...", true);

    fetch(docsPrefix + "versions.json", { credentials: "same-origin" })
      .then(response => {
        if (!response.ok) throw new Error("Version manifest unavailable");
        return response.json();
      })
      .then(rows => {
        if (!Array.isArray(rows)) throw new Error("Invalid version manifest");
        const versions = rows.filter(row => row && typeof row.version === "string" &&
          validVersion(row.version));
        const ids = new Set();
        const stable = versions.find(row => Array.isArray(row.aliases) &&
          row.aliases.includes("stable") && row.version !== "dev");
        const items = [];
        if (stable) items.push({ value: "stable", name: "Stable (" + stable.version + ")" });
        if (versions.some(row => row.version === "dev")) items.push({ value: "dev", name: "dev" });
        for (const row of versions) {
          if (row.version !== "dev")
            items.push({ value: row.version, name: row.version });
        }
        if (items.length === 0) throw new Error("No supported versions");
        select.replaceChildren();
        const active = preview ? "preview" : stable && current === stable.version ? "stable" : current;
        if (preview) option("preview", "PR preview", true);
        for (const item of items) {
          if (!ids.has(item.value)) {
            option(item.value, item.name, item.value === active);
            ids.add(item.value);
          }
        }
        if (active && active !== "preview" && !ids.has(active))
          option(active, active + " (archived)", true);
        select.disabled = false;
      })
      .catch(() => {
        select.replaceChildren();
        option("unavailable", "Versions unavailable", true);
        select.disabled = true;
      });

    select.addEventListener("change", () => {
      const value = select.value;
      if (value !== "stable" && !validVersion(value)) return;
      // Always navigate to a crate root: deep Rust API items may have changed
      // between releases and must not become false cross-version links.
      window.location.assign(docsPrefix + value + "/rust-api/quprs/");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render, { once: true });
  } else {
    render();
  }
})();
