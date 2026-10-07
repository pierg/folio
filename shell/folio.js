/* folio: the shell's one script.
   It draws, on every page, what metadata and the generated indices say: the top bar,
   the library rail, the header, the banners, the page panel, guide navigation, map rows, the home page's maps, topic focus, the
   journal timeline, search, previews, concept popovers and, when served by `folio serve`,
   the comment panel and the Review page, and KaTeX math on a page that asks for it. The page holds its
   <head> metadata and its <main>, which is a free canvas: it may carry its own style and script, and lays
   itself out in the room between the rail and the panel, or in the reading column when it asks for one. */
(function () {
  "use strict";

  var script = document.currentScript;
  var BASE = (function () {
    var src = script ? new URL(script.src, location.href).pathname : "/shell/folio.js";
    return src.replace(/shell\/folio\.js$/, "");
  })();
  var STORE = "folio:";
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  /* ------------------------------------------------------------ helpers */
  function el(tag, attrs, kids) {
    var node = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) continue;
      if (k === "text") node.textContent = v;
      else if (k === "html") node.innerHTML = v;
      else if (k.slice(0, 2) === "on") node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    (kids || []).forEach(function (kid) {
      if (kid === null || kid === undefined || kid === false) return;
      node.appendChild(typeof kid === "string" ? document.createTextNode(kid) : kid);
    });
    return node;
  }
  function icon(name) {
    var paths = {
      search: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4",
      moon: "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z",
      sun: "M12 4V2M12 22v-2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
      journal: "M6 3h11a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6zM6 3v18M10 8h5M10 12h5",
      alert: "M12 3 2 20h20L12 3zM12 10v4M12 17h0",
      info: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM12 11v6M12 7h0",
      chat: "M4 5h16v11H9l-5 4z",
      close: "M6 6l12 12M18 6 6 18",
      expand: "M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7",
      home: "M4 11 12 4l8 7M6 9.5V20h12V9.5",
      rail: "M4 5h16v14H4zM9.5 5v14",
      focus: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 11.5v1",
      copy: "M9 9h11v11H9zM5 15H4V4h11v1",
      check: "M5 12.5 10 17.5 19 7"
    };
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "f-icon");
    svg.setAttribute("aria-hidden", "true");
    var p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", paths[name]);
    svg.appendChild(p);
    return svg;
  }
  function meta(name) {
    var m = document.querySelector('meta[name="' + name + '"]');
    return m ? m.getAttribute("content") || "" : "";
  }
  function tagsOf(raw) {
    if (!raw) return [];
    if (Array.isArray(raw)) return raw.map(String);
    return String(raw).split(",").map(function (t) { return t.trim(); }).filter(Boolean);
  }
  function fetchJSON(path) {
    return fetch(BASE + path, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(path + ": " + r.status);
      return r.json();
    });
  }
  function optional(promise, fallback) { return promise.catch(function () { return fallback; }); }
  function store(key, value) {
    try {
      if (value === undefined) return localStorage.getItem(STORE + key);
      if (value === null) localStorage.removeItem(STORE + key); else localStorage.setItem(STORE + key, value);
    } catch (e) { return null; }
    return null;
  }
  function fmtDate(iso) {
    if (!iso) return "";
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso));
    if (!m) return String(iso);
    return parseInt(m[3], 10) + " " + MONTHS[parseInt(m[2], 10) - 1] + " " + m[1];
  }
  function human(name) { return String(name).replace(/[_-]+/g, " ").replace(/^./, function (c) { return c.toUpperCase(); }); }
  function href(url) { return url && url.charAt(0) === "/" ? BASE.replace(/\/$/, "") + siteURL(url) : url; }
  /* A Markdown record is served as a page at the same path with .html. */
  function siteURL(url) { return /\.md(#.*)?$/.test(url) ? url.replace(/\.md(#|$)/, ".html$1") : url; }
  function relOf(pathname) {
    var p = decodeURIComponent(pathname);
    if (p.indexOf(BASE) === 0) p = p.slice(BASE.length); else p = p.replace(/^\//, "");
    if (p === "" || /\/$/.test(p)) p += "index.html";
    return p;
  }
  function slug(text) { return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "section"; }

  /* -------------------------------------------------------------- data */
  var D = { catalog: [], byPath: {}, byFile: {}, byId: {}, backlinks: {}, nav: {}, site: {}, journal: null, search: null };

  function index(catalog) {
    D.catalog = catalog.documents || [];
    D.catalog.forEach(function (doc) {
      D.byPath[doc.path] = doc;
      D.byFile[doc.path] = { doc: doc, part: null };
      (doc.parts || []).forEach(function (part) { D.byFile[part.path] = { doc: doc, part: part }; });
      (D.byId[idKey(doc.id)] = D.byId[idKey(doc.id)] || []).push(doc);
    });
  }
  /* Ids compare without regard to case: `r-12` finds `R-12`. */
  function idKey(id) { return String(id).toLowerCase(); }
  function byId(id) { return D.byId[idKey(id)] || []; }
  /* A chip linking a document by its title, with its genre, so a source and its reading stay apart. */
  function docChip(d) {
    return el("a", { href: docURL(d), title: d.description }, [el("span", { class: "f-genre", text: d.genre }), " " + d.title]);
  }
  /* The document a site file belongs to: a page, a rendered record, a folder's index. */
  function lookup(rel) {
    if (D.byFile[rel]) return D.byFile[rel];
    if (/\.html$/.test(rel)) {
      var md = rel.replace(/\.html$/, ".md");
      if (D.byFile[md]) return D.byFile[md];
    }
    return null;
  }
  function lookupHref(a) {
    var url;
    try { url = new URL(a.getAttribute("href"), location.href); } catch (e) { return null; }
    if (url.origin !== location.origin) return null;
    return lookup(relOf(url.pathname));
  }
  function docURL(doc) { return href(doc.url); }
  function byKey(path) { return D.byPath[path]; }
  function dateOf(path) {
    var doc = byKey(path) || {};
    if (doc.created || doc.updated) return { created: doc.created, updated: doc.updated };
    return (D.site.dates || {})[path] || {};
  }

  /* --------------------------------------------------------- topic focus */
  /* A reader can focus the library on one or more topics, the charter's home maps. The
     catalog gives each document the topics it falls under (`topics`, written by
     `folio index`), so a document is in focus when one of them is chosen. The choice is
     kept in this browser; a page outside it still opens by its address. */
  var FOCUS = [];
  function topicMaps() {
    return (((D.site.home || {}).maps) || []).map(function (id) {
      return byId(id).filter(function (d) { return d.rows; })[0];
    }).filter(Boolean);
  }
  function loadFocus() {
    var ids = [];
    try { ids = JSON.parse(store("focus") || "[]"); } catch (e) { ids = []; }
    var known = topicMaps().map(function (m) { return m.id; });
    FOCUS = Array.isArray(ids) ? known.filter(function (id) { return ids.indexOf(id) >= 0; }) : [];
  }
  function focused() { return FOCUS.length > 0; }
  function inFocus(doc) {
    if (!focused() || !doc) return true;
    return (doc.topics || []).some(function (t) { return FOCUS.indexOf(t) >= 0; });
  }
  /* The document a site file belongs to is in focus: a part follows its document. */
  function pathInFocus(path) { var info = path ? lookup(path) : null; return !info || inFocus(info.doc); }
  function focusNames() {
    return FOCUS.map(function (id) { var m = byId(id)[0]; return m ? m.title : id; }).join(", ");
  }
  function setFocus(ids) {
    store("focus", ids.length ? JSON.stringify(ids) : null);
    location.reload();
  }
  function clearFocusButton(label) {
    return el("button", { type: "button", class: "f-focus-clear", text: label || "Clear focus", onclick: function () { setFocus([]); } });
  }

  /* The top bar's control: a button, or, while a focus is on, a chip naming it. Either
     opens a menu of the home maps; the choice applies when the menu closes. */
  function focusControl() {
    var maps = topicMaps();
    if (maps.length < 2) return null;
    var wrap = el("div", { class: "f-focus" });
    var menu = null, opener;
    function count(map) {
      return D.catalog.filter(function (d) { return d.genre !== "journal" && d.id !== "home" && (d.topics || []).indexOf(map.id) >= 0; }).length;
    }
    function close(apply) {
      if (!menu) return;
      var picked = Array.prototype.filter.call(menu.querySelectorAll("input"), function (i) { return i.checked; })
        .map(function (i) { return i.value; });
      menu.remove(); menu = null;
      opener.setAttribute("aria-expanded", "false");
      document.removeEventListener("click", outside, true);
      if (apply && picked.join(",") !== FOCUS.join(",")) setFocus(picked);
    }
    function outside(e) { if (menu && !wrap.contains(e.target)) close(true); }
    function open() {
      if (menu) { close(true); return; }
      var list = el("ul");
      maps.forEach(function (m) {
        list.appendChild(el("li", null, [el("label", null, [
          el("input", { type: "checkbox", value: m.id, checked: FOCUS.indexOf(m.id) >= 0 }),
          el("span", { class: "f-focus-name", text: m.title }),
          el("span", { class: "f-count", text: String(count(m)) })])]));
      });
      menu = el("div", { class: "f-focus-menu", role: "dialog", "aria-label": "Focus on topics" }, [
        el("p", { class: "f-focus-help", text: "Show only the documents under these maps, with the concepts they use and the journal entries about them." }),
        list,
        el("div", { class: "f-focus-actions" }, [
          el("button", { type: "button", class: "f-btn", text: "Show everything", onclick: function () {
            Array.prototype.forEach.call(menu.querySelectorAll("input"), function (i) { i.checked = false; }); close(true); } }),
          el("button", { type: "button", class: "f-btn f-focus-done", text: "Done", onclick: function () { close(true); } })])
      ]);
      menu.addEventListener("keydown", function (e) { if (e.key === "Escape") { e.stopPropagation(); close(false); opener.focus(); } });
      wrap.appendChild(menu);
      opener.setAttribute("aria-expanded", "true");
      var first = menu.querySelector("input");
      if (first) first.focus({ preventScroll: true });
      setTimeout(function () { document.addEventListener("click", outside, true); }, 0);
    }
    if (focused()) {
      opener = el("button", { type: "button", class: "f-focus-name-btn", "aria-haspopup": "dialog", "aria-expanded": "false",
        title: "Focused on " + focusNames() + ". Change the focus", onclick: open },
        [icon("focus"), el("span", { class: "f-focus-label", text: focusNames() })]);
      wrap.appendChild(el("div", { class: "f-focus-chip" }, [opener,
        el("button", { type: "button", class: "f-focus-x", "aria-label": "Clear focus", title: "Clear focus", onclick: function () { setFocus([]); } }, [icon("close")])]));
    } else {
      opener = el("button", { type: "button", class: "f-btn f-focus-btn", "aria-haspopup": "dialog", "aria-expanded": "false",
        title: "Focus on topics", onclick: open }, [icon("focus"), el("span", { class: "f-label", text: "Focus" })]);
      wrap.appendChild(opener);
    }
    return wrap;
  }

  /* --------------------------------------------------------------- theme */
  function applyTheme(choice) {
    if (choice === "light" || choice === "dark") document.documentElement.setAttribute("data-theme", choice);
    else document.documentElement.removeAttribute("data-theme");
  }
  applyTheme(store("theme"));
  // The library rail's place on a wide screen, set before the page paints so it never jumps.
  if (store("rail") === "closed") document.documentElement.setAttribute("data-rail", "closed");
  function currentTheme() {
    var set = document.documentElement.getAttribute("data-theme");
    if (set) return set;
    return window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  /* -------------------------------------------------------------- frame */
  var main, page, panel;

  function frame(view, rel) {
    main = document.querySelector("main") || el("main");
    page = el("article", { class: "f-page" });
    panel = el("aside", { class: "f-panel", "aria-label": "About this page" });
    var layout = el("div", { class: "f-layout" }, [page, panel]);
    if (!main.parentNode) document.body.appendChild(main);
    main.parentNode.insertBefore(layout, main);
    page.appendChild(main);
    var side = rail(view, rel);
    if (side) {
      document.body.insertBefore(el("div", { class: "f-rail-backdrop", onclick: function () { setRail(false); } }), document.body.firstChild);
      document.body.insertBefore(side, document.body.firstChild);
    }
    document.body.insertBefore(topbar(view, !!side), document.body.firstChild);
    if (side) {
      syncRail(); keepInView(side);
      // A page prerendered on hover drew its rail before the click: place it again when it is shown.
      if (document.prerendering) document.addEventListener("prerenderingchange", function () { keepInView(side); }, { once: true });
    }
    wrapTables();
  }

  function topbar(view, hasRail) {
    var themeBtn = el("button", { class: "f-btn", type: "button", "aria-label": "Switch theme", title: "Switch theme" });
    function paintTheme() {
      themeBtn.textContent = "";
      themeBtn.appendChild(icon(currentTheme() === "dark" ? "sun" : "moon"));
    }
    themeBtn.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      applyTheme(next); store("theme", next); paintTheme();
    });
    paintTheme();
    var journalURL = href((D.site.journal || {}).url || "/content/journal/");
    var mac = /Mac|iPhone|iPad/.test(navigator.platform || "");
    return el("header", { class: "f-top" }, [
      hasRail ? el("button", { class: "f-btn f-rail-btn", type: "button", "aria-label": "Library", "aria-controls": "f-rail",
        "aria-expanded": "false", title: "Library  [", onclick: function () { setRail(!railShown()); } }, [icon("rail")]) : null,
      el("a", { class: "f-brand", href: BASE + "content/" }, [el("span", { text: D.site.name || "Library" })]),
      el("nav", { class: "f-nav", "aria-label": "Library" }, [
        el("a", { href: journalURL, "aria-current": view === "journal" ? "page" : null },
          [icon("journal"), el("span", { class: "f-label", text: "Journal" })]),
        D.site.comments ? el("a", { href: href(((D.site.review || {}).url) || "/content/review/"), "aria-current": view === "review" ? "page" : null },
          [icon("chat"), el("span", { class: "f-label", text: "Review" })]) : null,
        focusControl(),
        el("button", { class: "f-btn f-search-btn", type: "button", onclick: openSearch, "aria-label": "Search" },
          [icon("search"), el("span", { class: "f-label", text: "Search" }), el("kbd", { text: mac ? "⌘K" : "Ctrl K" })]),
        themeBtn
      ])
    ]);
  }

  function wrapTables() {
    Array.prototype.forEach.call(main.querySelectorAll("table"), function (t) {
      if (t.parentNode.classList.contains("f-scroll")) return;
      var box = el("div", { class: "f-scroll" });
      t.parentNode.insertBefore(box, t);
      box.appendChild(t);
    });
  }

  /* --------------------------------------------------------- library rail */
  /* The library on the left of every page: the charter's home maps, each with the documents
     it lists, then every document by genre. All of it comes from the catalog, the guides'
     nav and the site data. A group the reader opens or closes is remembered in this browser. */
  var NARROW = "(max-width: 77.99rem)";
  function narrow() { return !!(window.matchMedia && matchMedia(NARROW).matches); }
  function plural(word) {
    var w = human(word);
    if (/[^aeiou]y$/.test(w)) return w.slice(0, -1) + "ies";
    if (/(s|x|ch|sh)$/.test(w)) return w + "es";
    return w + "s";
  }
  function isRecordId(id) { return /^[A-Za-z]+-\d+$/.test(String(id || "")); }

  /* A genre's mark in the rail: a letter or two, its name on hover and in the rail's key. */
  var MARKS = { concept: "C", note: "N", entry: "E", guide: "G", map: "M", journal: "J", paper: "P", project: "Pj",
    reading: "R", source: "S", survey: "Sv", question: "Q", protocol: "Pr", result: "Rs", claim: "Cl", report: "Rp" };
  function markOf(genre) { return MARKS[genre] || human(genre).slice(0, 2); }
  /* The order a reader meets genres in: the way in first, then ideas, then the evidence. */
  var READING = ["guide", "entry", "concept", "note", "survey", "reading", "source", "map"];
  function genreRank(genre) { var i = READING.indexOf(genre); return i < 0 ? READING.length : i; }
  function summary(docs) {
    var n = {};
    docs.forEach(function (d) { n[d.genre] = (n[d.genre] || 0) + 1; });
    return Object.keys(n).sort(function (a, b) { return genreRank(a) - genreRank(b) || a.localeCompare(b); })
      .map(function (g) { return n[g] + " " + (n[g] === 1 ? g : plural(g).toLowerCase()); }).join(", ");
  }
  /* A map's documents as the rail lists them: under the map's own headings when it has two or more;
     else, for a long map, by genre in reading order; else as one list. */
  function sectionsOf(map, docs) {
    var shownHere = {};
    docs.forEach(function (d) { shownHere[d.path] = d; });
    var parts = (map.sections || []).map(function (sec) {
      return { title: sec.title, docs: sec.rows.map(function (p) { return shownHere[p]; }).filter(Boolean) };
    }).filter(function (part) { return part.docs.length; });
    if (parts.filter(function (part) { return part.title; }).length >= 2) {
      var placed = {};
      parts.forEach(function (part) { part.docs.forEach(function (d) { placed[d.path] = 1; }); });
      var rest = docs.filter(function (d) { return !placed[d.path]; });
      if (rest.length) parts.push({ title: "More", docs: rest });
      return parts;
    }
    if (docs.length <= 6) return [{ title: null, docs: docs }];
    var by = {};
    docs.forEach(function (d) { (by[d.genre] = by[d.genre] || []).push(d); });
    return Object.keys(by).sort(function (a, b) { return genreRank(a) - genreRank(b) || a.localeCompare(b); })
      .map(function (g) { return { title: plural(g), docs: by[g] }; });
  }

  function rail(view, rel) {
    if (!D.catalog.length) return null;
    var info = view ? null : lookup(rel);
    var hereDoc = info ? info.doc : null;
    var herePath = info ? (info.part || info.doc).path : null;
    var box = el("nav", { class: "f-rail", id: "f-rail", "aria-label": "Library" });
    var shown = {};  // documents already visible in an open group, so a genre group stays closed
    var marked = {};  // the genres whose mark the rail shows, for its key

    function item(doc, opts) {
      opts = opts || {};
      var cur = hereDoc === doc;
      var out = !inFocus(doc);
      if (opts.mark) marked[doc.genre] = 1;
      var a = el("a", { href: docURL(doc), title: doc.title + (out ? " (outside your focus)" : ""),
        "aria-current": cur && herePath === doc.path ? "page" : null,
        class: ((cur ? "f-here" : "") + (out ? " f-out" : "")).trim() || null }, [
        opts.mark ? el("span", { class: "f-gmark", "data-g": doc.genre, title: human(doc.genre), text: markOf(doc.genre) }) : null,
        isRecordId(doc.id) ? el("span", { class: "f-rid", text: doc.id }) : null,
        el("span", { class: "f-rname", text: doc.title }),
        opts.start ? el("span", { class: "f-start", text: "Start" }) : null
      ]);
      var li = el("li", null, [a]);
      // A guide shows its chapters while the reader is in it.
      var guide = D.nav[doc.path];
      if (cur && guide && guide.chapters && guide.chapters.length) {
        var ol = el("ol", { class: "f-rchapters" });
        guide.chapters.forEach(function (ch) {
          ol.appendChild(el("li", null, [el("a", { href: href(ch.url), title: ch.title, text: ch.title,
            "aria-current": herePath === ch.path ? "page" : null })]));
        });
        li.appendChild(ol);
      }
      return li;
    }
    /* A group opens as the reader last left it, or by default; and always when it holds the
       current page and no open group above already shows it. */
    function group(key, head, docs, byDefault, fill, count) {
      var holdsHere = !!hereDoc && docs.indexOf(hereDoc) >= 0;
      var saved = store("rail:" + key);
      var open = (holdsHere && !shown[hereDoc.path]) || (saved ? saved === "open" : byDefault);
      var ul = el("ul", { class: "f-rlist", id: "f-r-" + slug(key) });
      if (fill) fill(ul); else docs.forEach(function (d) { ul.appendChild(item(d)); });
      var caret = el("button", { class: "f-caret", type: "button", "aria-expanded": String(open), "aria-controls": ul.id,
        "aria-label": (open ? "Close " : "Open ") + head.textContent });
      var wrap = el("div", { class: "f-rgroup" + (holdsHere ? " f-holds" : ""), "data-open": open ? "" : null }, [
        el("div", { class: "f-rhead" }, [caret, head, count || el("span", { class: "f-count", text: String(docs.length) })]), ul]);
      function flip() {
        open = !open;
        if (open) wrap.setAttribute("data-open", ""); else wrap.removeAttribute("data-open");
        caret.setAttribute("aria-expanded", String(open));
        caret.setAttribute("aria-label", (open ? "Close " : "Open ") + head.textContent);
        store("rail:" + key, open ? "open" : "closed");
      }
      caret.addEventListener("click", flip);
      if (head.tagName === "BUTTON") head.addEventListener("click", flip);
      if (open) docs.forEach(function (d) { shown[d.path] = 1; });
      return wrap;
    }
    function section(label, kids) {
      if (!kids.length) return;
      box.appendChild(el("div", { class: "f-rsection" }, [el("h2", { text: label })].concat(kids)));
    }

    // Home, the journal and, when served, the Review page.
    var home = byId("home").filter(function (d) { return d.rows; })[0];
    var journal = D.catalog.filter(function (d) { return d.genre === "journal" && inFocus(d); });
    var links = el("ul", { class: "f-rlinks" });
    function link(url, label, iconName, current, count) {
      links.appendChild(el("li", null, [el("a", { href: url, "aria-current": current === true ? "page" : null,
        class: current === "near" ? "f-near" : null },
        [icon(iconName), el("span", { text: label }), count ? el("span", { class: "f-count", text: String(count) }) : null])]));
    }
    link(home ? docURL(home) : BASE + "content/", "Home", "home", !!(home && hereDoc === home));
    link(href((D.site.journal || {}).url || "/content/journal/"), "Journal", "journal",
      view === "journal" ? true : hereDoc && hereDoc.genre === "journal" ? "near" : false, journal.length);
    if (D.site.comments) link(reviewURL(), "Review", "chat", view === "review");
    box.appendChild(links);
    if (focused()) box.appendChild(el("div", { class: "f-rfocus" }, [icon("focus"),
      el("span", null, ["Focus: ", el("strong", { text: focusNames() })]), clearFocusButton("Clear")]));

    // The charter's home maps, in its order: each the documents it lists.
    var maps = [];
    (((D.site.home || {}).maps) || []).forEach(function (id) {
      var map = byId(id).filter(function (d) { return d.rows; })[0];
      if (!map || !inFocus(map)) return;
      var docs = (map.rows || []).map(byKey).filter(function (d) { return d && d.status !== "draft" && inFocus(d); });
      var name = el("a", { class: "f-rmap", href: docURL(map), title: map.description, text: map.title,
        "aria-current": hereDoc === map ? "page" : null });
      if (!docs.length) {
        maps.push(el("div", { class: "f-rgroup f-rsolo" }, [el("div", { class: "f-rhead" }, [name])]));
        return;
      }
      var parts = sectionsOf(map, docs);
      maps.push(group("map:" + map.id, name, docs, true, function (ul) {
        var many = docs.length > 12;  // a long map opens its first section and the one being read
        parts.forEach(function (part, i) {
          if (!part.title) {
            part.docs.forEach(function (d) { ul.appendChild(item(d, { mark: true, start: d === docs[0] && docs.length > 2 })); });
            return;
          }
          var head = el("button", { class: "f-rname-btn f-rsec-btn", type: "button", title: part.title, text: part.title });
          var sum = el("span", { class: "f-rsum", text: summary(part.docs) });
          ul.appendChild(el("li", { class: "f-rsec" }, [group("sec:" + map.id + ":" + slug(part.title), head, part.docs, !many || i === 0,
            function (sub) {
              part.docs.forEach(function (d) { sub.appendChild(item(d, { mark: true, start: d === docs[0] && docs.length > 2 })); });
            }, sum)]));
        });
      }));
    });
    section("Maps", maps);

    // Every document by genre; journal entries live in the journal, the home page above.
    var genres = {};
    D.catalog.forEach(function (d) {
      if (d.genre === "journal" || d === home) return;
      if (!inFocus(d) && d !== hereDoc) return;  // the page being read stays in the rail, marked
      (genres[d.genre] = genres[d.genre] || []).push(d);
    });
    var byGenre = Object.keys(genres).sort().map(function (g) {
      var docs = genres[g].slice().sort(function (a, b) {
        return isRecordId(a.id) && isRecordId(b.id) ? a.id.localeCompare(b.id, undefined, { numeric: true }) : a.title.localeCompare(b.title);
      });
      return group("genre:" + g, el("button", { class: "f-rname-btn", type: "button", text: plural(g) }), docs, false);
    });
    section("By genre", byGenre);

    var used = Object.keys(marked).sort(function (a, b) { return genreRank(a) - genreRank(b) || a.localeCompare(b); });
    if (used.length) box.appendChild(el("p", { class: "f-rlegend" }, used.map(function (g) {
      return el("span", null, [el("span", { class: "f-gmark", "data-g": g, text: markOf(g) }), " " + g]);
    })));
    box.appendChild(el("p", { class: "f-rkeys" }, [el("kbd", { text: "[" }), " shows or hides the library"]));
    box.addEventListener("click", function (e) {
      var a = e.target.closest && e.target.closest("a");
      if (!a) return;
      // Where the clicked link sat in the rail, so the next page can put it back under the pointer.
      try {
        sessionStorage.setItem(STORE + "rail-at", JSON.stringify({
          href: a.getAttribute("href"), y: a.getBoundingClientRect().top - box.getBoundingClientRect().top }));
      } catch (err) { /* storage off: the rail falls back to keeping the current page in view */ }
      if (narrow()) setRail(false);
    });
    return box;
  }

  /* Wide: the rail sits beside the page, shown unless the reader hid it (remembered).
     Narrow: it is a drawer over the page, closed on each page. */
  function railShown() {
    if (!document.getElementById("f-rail")) return false;
    return narrow() ? document.body.classList.contains("f-rail-open") : document.documentElement.getAttribute("data-rail") !== "closed";
  }
  function setRail(open) {
    if (!document.getElementById("f-rail")) return;
    if (narrow()) document.body.classList.toggle("f-rail-open", open);
    else {
      store("rail", open ? null : "closed");
      if (open) document.documentElement.removeAttribute("data-rail");
      else document.documentElement.setAttribute("data-rail", "closed");
    }
    syncRail();
    if (open && narrow()) { var first = document.querySelector("#f-rail a"); if (first) first.focus({ preventScroll: true }); }
  }
  function syncRail() {
    var side = document.getElementById("f-rail");
    if (!side) return;
    var open = railShown();
    side.inert = !open;
    document.body.classList.add("f-has-rail");
    Array.prototype.forEach.call(document.querySelectorAll(".f-rail-btn"), function (b) { b.setAttribute("aria-expanded", String(open)); });
  }
  /* The current page's row, in view in a long rail. */
  function keepInView(side) {
    /* A link clicked in the rail goes back to the height it was clicked at, so the pointer still rests
       on it, however the groups above it opened or closed on the new page. */
    var at = null;
    try { at = JSON.parse(sessionStorage.getItem(STORE + "rail-at") || "null"); } catch (err) { at = null; }
    if (at && at.href) {
      var same = Array.prototype.filter.call(side.querySelectorAll("a[href]"), function (a) { return a.getAttribute("href") === at.href; });
      var link = same.filter(function (a) { return a.getAttribute("aria-current") === "page"; })[0] || same[0];
      if (link) {
        side.scrollTop += (link.getBoundingClientRect().top - side.getBoundingClientRect().top) - at.y;
        if (!document.prerendering) { try { sessionStorage.removeItem(STORE + "rail-at"); } catch (err) { /* nothing to clear */ } }
        return;
      }
    }
    var cur = side.querySelector('[aria-current="page"]') || side.querySelector(".f-here");
    if (!cur) return;
    var top = cur.getBoundingClientRect().top - side.getBoundingClientRect().top + side.scrollTop;
    if (top > side.clientHeight - 80) side.scrollTop = top - side.clientHeight / 3;
  }
  window.addEventListener("resize", function () {
    if (!narrow()) document.body.classList.remove("f-rail-open");
    syncRail();
  });

  /* ------------------------------------------------------------- header */
  function statusPill(status) {
    if (!status || status === "live") return null;
    return el("span", { class: "f-status", "data-s": status, text: status });
  }

  function valueNode(value) {
    if (Array.isArray(value)) {
      var span = el("span");
      value.forEach(function (v, i) { if (i) span.appendChild(document.createTextNode(", ")); span.appendChild(valueNode(v)); });
      return span;
    }
    var text = String(value);
    var target = byId(text);
    if (target && target.length) {
      var t = target[0];
      return el("a", { href: docURL(t), title: t.description, text: /^[A-Za-z]+-\d+$/.test(t.id) ? t.id + " · " + t.title : t.title });
    }
    if (/^https?:\/\//.test(text)) return el("a", { href: text, text: text.replace(/^https?:\/\//, "") });
    if ((/\//.test(text) && !/\s/.test(text)) || /['"$|`]/.test(text)) return el("code", { text: text });
    return document.createTextNode(text);
  }

  /* Fields the header shows in its own way, not in the facts list. */
  var OWN = { about: 1, date: 1, kind: 1, reviewed: 1, supersedes: 1, replaced_by: 1 };

  // The page's path in the library, as an agent or a command takes it: a folder page by its folder.
  function copyPath(path) {
    var label = el("span", { text: path });
    var mark = icon("copy");
    var btn = el("button", { type: "button", class: "f-copypath", title: "Copy the path of this page",
      "aria-label": "Copy the path " + path }, [mark, label]);
    function done(ok) {
      btn.replaceChild(icon(ok ? "check" : "copy"), btn.firstChild);
      label.textContent = ok ? "Copied" : "Copy failed: " + path;
      setTimeout(function () { btn.replaceChild(icon("copy"), btn.firstChild); label.textContent = path; }, 1400);
    }
    function fallback() {
      var area = el("textarea", { class: "f-offscreen", "aria-hidden": "true" });
      area.value = path;
      document.body.appendChild(area);
      area.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      area.remove();
      return ok;
    }
    btn.addEventListener("click", function () {
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(path).then(function () { done(true); }, function () { done(fallback()); });
      } else {
        done(fallback());
      }
    });
    return btn;
  }

  function header(info) {
    var doc = info ? info.doc : null;
    var part = info ? info.part : null;
    var genre = meta("genre") || (doc && doc.genre) || "";
    var isHome = !!(doc && doc.id === "home");
    // The home page's title is the charter's name, never one the page carries.
    var title = (isHome && D.site.name) || meta("title") || (part && part.title) || (doc && doc.title) || document.title;
    var description = meta("description") || (part && part.description) || (doc && doc.description) ||
      (isHome && D.site.purpose) || "";
    var status = doc ? doc.status : meta("status");
    var fields = (doc && doc.fields) || {};
    var tags = doc ? doc.tags : tagsOf(meta("tags"));

    var eyebrow = el("div", { class: "f-eyebrow" });
    var guide = part && part.number && D.nav[doc.path];
    if (guide) {
      eyebrow.appendChild(el("a", { href: docURL(doc), text: doc.title }));
      eyebrow.appendChild(el("span", { class: "f-sep", text: "/" }));
      eyebrow.appendChild(el("span", { text: "Chapter " + part.number + " of " + guide.chapters.length }));
    } else if (doc && doc.id === "home") {
      eyebrow.appendChild(el("span", { text: "Home" }));
    } else if (genre) {
      eyebrow.appendChild(el("span", { text: genre }));
      if (doc && doc.id && /^[A-Za-z]+-\d+$/.test(doc.id)) eyebrow.appendChild(el("span", { class: "f-id", text: doc.id }));
      if (fields.kind) eyebrow.appendChild(el("span", { class: "f-kind", "data-kind": fields.kind, text: fields.kind }));
    }

    var metaRow = el("div", { class: "f-meta" });
    var pill = statusPill(status);
    if (pill) metaRow.appendChild(pill);
    if (fields.date) metaRow.appendChild(el("span", null, [el("time", { datetime: fields.date, text: fmtDate(fields.date) })]));
    if (fields.reviewed) metaRow.appendChild(el("span", null, ["Reviewed ", el("time", { datetime: fields.reviewed, text: fmtDate(fields.reviewed) })]));
    var frozenOn = doc ? (D.site.frozen || {})[doc.path] : null;
    if (frozenOn) metaRow.appendChild(el("span", { class: "f-frozen" }, ["Frozen since ", el("time", { datetime: frozenOn, text: fmtDate(frozenOn) })]));
    var dates = doc ? dateOf(doc.path) : {};
    if (dates.created && !fields.date) metaRow.appendChild(el("span", null, ["Created ", el("time", { datetime: dates.created, text: fmtDate(dates.created) })]));
    if (dates.updated && dates.updated !== dates.created && !fields.date)
      metaRow.appendChild(el("span", null, ["Updated ", el("time", { datetime: dates.updated, text: fmtDate(dates.updated) })]));
    if (tags.length) {
      var tagBox = el("span", { class: "f-tags" });
      tags.forEach(function (t) { tagBox.appendChild(el("button", { type: "button", class: "f-tag", title: "Search for " + t, text: t, onclick: function () { openSearch(t); } })); });
      metaRow.appendChild(tagBox);
    }

    var source = (part || doc || {}).path;
    if (source) eyebrow.appendChild(copyPath(source.replace(/(^|\/)index\.html$/, "$1")));

    var outside = doc && !isHome && !inFocus(doc);
    var head = el("header", { class: "f-head" }, [
      eyebrow.childNodes.length ? eyebrow : null,
      el("h1", { class: "f-title", text: title }),
      description ? el("p", { class: "f-sub", text: description }) : null,
      metaRow.childNodes.length ? metaRow : null,
      outside ? el("p", { class: "f-outside" }, [icon("focus"),
        el("span", { text: "Outside your focus on " + focusNames() + "." }), clearFocusButton()]) : null
    ]);

    if (fields.about && fields.about.length) {
      var about = el("div", { class: "f-about" });
      fields.about.forEach(function (id) {
        var target = byId(id)[0];
        about.appendChild(target ? docChip(target) : el("span", { text: id }));
      });
      head.appendChild(about);
    }

    var facts = el("dl", { class: "f-facts" });
    // The card's declared order, never alphabetical.
    var order = (doc && doc.field_order) || Object.keys(fields);
    order.forEach(function (name) {
      if (!(name in fields)) return;
      if (OWN[name] || fields[name] === null || fields[name] === "") return;
      facts.appendChild(el("dt", { text: human(name) }));
      var dd = el("dd", null, [valueNode(fields[name])]);
      if (name === "number") dd.className = "f-big";
      facts.appendChild(dd);
    });
    head.appendChild(el("div", { class: "f-banners" }));
    if (facts.childNodes.length && (!part || part.part !== "chapter")) head.appendChild(facts);
    page.insertBefore(head, main);
    document.title = title + (D.site.name && doc && doc.id !== "home" ? " · " + D.site.name : "");
  }

  /* ------------------------------------------------------------ banners */
  function banner(kind, iconName, title, body, link) {
    var box = el("div", { class: "f-banner f-banner-" + kind, role: "note" }, [icon(iconName), el("div", null, [
      el("strong", { text: title }), " ",
      link ? el("a", { href: link.href, text: link.text }) : null,
      body ? el("p", { text: body }) : null
    ])]);
    var slot = page.querySelector(".f-banners");
    if (slot) slot.appendChild(box); else page.insertBefore(box, main);
  }

  function banners(doc, links) {
    (links.superseded_by || []).forEach(function (path) {
      var newer = byKey(path);
      if (newer) banner("superseded", "alert", "Superseded by " + newer.id + ".", "This record stays at its address so old citations still show what they cited.",
        { href: docURL(newer), text: newer.title });
    });
    (links.retracted_by || []).forEach(function (path) {
      var entry = byKey(path);
      if (entry) banner("retracted", "alert", "Retracted on " + fmtDate((entry.fields || {}).date) + ".", entry.description,
        { href: docURL(entry), text: entry.title });
    });
    if (doc.status === "retired" && (doc.fields || {}).replaced_by) {
      var to = byId(doc.fields.replaced_by)[0];
      var lib = String(doc.fields.replaced_by).split(":");
      var other = lib.length > 1 && ((D.site.libraries || {})[lib[0]] || null);
      if (to) banner("retired", "alert", "Retired.", null, { href: docURL(to), text: "Read " + to.title + " instead" });
      else if (other) banner("retired", "alert", "Retired.", null,
        { href: other.url || "#", text: "Read " + lib.slice(1).join(":") + " in " + lib[0] + " instead" });
    }
    var corrections = (links.about || []).filter(function (a) { return a.kind === "correction"; });
    if (!corrections.length) return;
    optional(loadSearch(), []).then(function (rows) {
      corrections.slice().reverse().forEach(function (a) {
        var entry = byKey(a.path);
        if (!entry) return;
        var text = "";
        rows.forEach(function (r) { if (r.path === a.path) text = r.text; });
        banner("correction", "info", "Correction, " + fmtDate(a.date) + ":", text || entry.description,
          { href: docURL(entry), text: entry.title });
      });
    });
  }

  /* ---------------------------------------------------------- the panel */
  function docList(paths, withDate) {
    var ul = el("ul");
    paths.forEach(function (path) {
      var doc = byKey(path);
      if (!doc) return;
      var date = withDate ? (doc.fields || {}).date : null;
      ul.appendChild(el("li", null, [
        el("span", { class: "f-genre", text: doc.genre + (/^[A-Za-z]+-\d+$/.test(doc.id) ? " · " + doc.id : "") }),
        el("a", { href: docURL(doc), title: doc.description, text: doc.title }),
        date ? el("span", { class: "f-when", text: fmtDate(date) }) : null
      ]));
    });
    return ul;
  }
  function panelSection(title, body, count, cls) {
    if (!body) return;
    panel.appendChild(el("section", { class: cls || null }, [
      el("h2", null, [title, count ? el("span", { class: "f-count", text: String(count) }) : null]), body
    ]));
  }

  function outline() {
    var heads = main.querySelectorAll("h2, h3");
    if (heads.length < 2) return;
    var ul = el("ul", { class: "f-outline" });
    var links = [];
    Array.prototype.forEach.call(heads, function (h) {
      if (!h.id) h.id = slug(h.textContent);
      var a = el("a", { href: "#" + h.id, class: h.tagName === "H3" ? "f-sub3" : null, text: h.textContent });
      links.push([h, a]);
      ul.appendChild(el("li", null, [a]));
    });
    panelSection("On this page", ul, null, "f-outline-box");
    if (!("IntersectionObserver" in window)) return;
    var io = new IntersectionObserver(function () {
      var top = null;
      links.forEach(function (pair) { if (pair[0].getBoundingClientRect().top < window.innerHeight * 0.3) top = pair; });
      links.forEach(function (pair) { pair[1].classList.toggle("f-on", pair === top); });
    }, { rootMargin: "0px 0px -60% 0px" });
    links.forEach(function (pair) { io.observe(pair[0]); });
  }

  var REVERSE = { supersedes: "Superseded by" };
  function linkPanels(doc, links) {
    var shown = {};
    Object.keys(links.fields || {}).forEach(function (name) {
      if (name === "supersedes") return;  // the banner says it
      links.fields[name].forEach(function (p) { shown[p] = 1; });
      var label = REVERSE[name] || ("As its " + name);
      panelSection(label, docList(links.fields[name], true), links.fields[name].length);
    });
    var about = (links.about || []).map(function (a) { shown[a.path] = 1; return a.path; });
    var rows = {};
    (doc.rows || []).forEach(function (p) { rows[p] = 1; });  // a map's rows are on the page already
    var cites = (links.cites || []).filter(function (p) { return p !== doc.path && !rows[p]; });
    var citedBy = (links.cited_by || []).filter(function (p) { return !shown[p] && !(links.superseded_by || []).includes(p); });
    if (cites.length) panelSection("Cites", docList(cites), cites.length);
    if (citedBy.length) panelSection("Cited by", docList(citedBy), citedBy.length);
    if (about.length) panelSection("In the journal", docList(about, true), about.length);
  }

  function detailsPanel(doc, rel) {
    var dl = el("dl");
    function row(k, v) { dl.appendChild(el("dt", { text: k })); dl.appendChild(el("dd", null, [v])); }
    row("Genre", document.createTextNode(doc.genre || ""));
    if (doc.id) row("Id", el("code", { text: doc.id }));
    row("File", el("code", { text: rel }));
    panelSection("Details", dl);
  }

  /* ------------------------------------------------------------- paper */
  /* A paper's landing page: the abstract read from its source, the current build's PDF,
     and its frozen versions. All of it comes from the catalog and the site data. */
  function paperLanding(doc) {
    var box = el("section", { class: "f-paper", "aria-label": "The paper" });
    if (doc.abstract) {
      var abs = el("div", { class: "f-abstract" }, [el("h2", { text: "Abstract" })]);
      doc.abstract.split(/\n\n+/).forEach(function (p) { abs.appendChild(el("p", { text: p })); });
      box.appendChild(abs);
    }
    var current = (D.site.builds || {})[doc.path];
    var versions = (doc.versions || []).slice().reverse();
    if (current || versions.length) {
      var files = el("div", { class: "f-paper-files" });
      if (current) files.appendChild(el("a", { class: "f-pdf", href: href(current) }, [el("strong", { text: "Read the PDF" }),
        el("span", { text: "the current build" })]));
      if (versions.length) {
        var ul = el("ul", { class: "f-versions" });
        versions.forEach(function (v) {
          var when = ((D.site.dates || {})[v.path] || {}).created;
          ul.appendChild(el("li", null, [
            el("span", { class: "f-vname", text: v.name }),
            when ? el("time", { datetime: when, text: "Frozen " + fmtDate(when) }) : el("span", { class: "f-when", text: "Not committed yet" }),
            v.pdf ? el("a", { href: href("/" + v.pdf), text: "PDF" }) : null
          ]));
        });
        files.appendChild(el("div", null, [el("h2", { text: "Versions" }), ul]));
      }
      box.appendChild(files);
    }
    if (box.childNodes.length) page.insertBefore(box, main);
  }

  /* ---------------------------------------------------------- map rows */
  function mapRows() {
    Array.prototype.forEach.call(main.querySelectorAll("ul.rows > li"), function (li) {
      var a = li.querySelector("a");
      if (!a) return;
      var info = lookupHref(a);
      if (!info) return;
      var doc = info.doc;
      var target = info.part || doc;
      // The row's text in the file is a fallback; the catalog's title is the one shown.
      if (target.title) a.textContent = target.title;
      if (!li.querySelector(".why") && target.description)
        li.appendChild(el("span", { class: "why f-derived", text: target.description }));
      var label = doc.genre + (doc.status && doc.status !== "live" ? " · " + doc.status : "");
      li.appendChild(el("span", { class: "f-genre", text: label }));
    });
  }

  /* ------------------------------------------------------------- guides */
  function guideNav(doc, part) {
    var guide = D.nav[doc.path];
    if (!guide) return;
    if (!part) {
      var ol = el("ol", { class: "f-chapters" });
      guide.chapters.forEach(function (ch) {
        ol.appendChild(el("li", null, [el("a", { href: href(ch.url), text: ch.title }), ch.description ? el("p", { text: ch.description }) : null]));
      });
      page.appendChild(el("section", { class: "f-section" }, [el("h2", { text: "Chapters" }), ol]));
      return;
    }
    var i = guide.chapters.findIndex(function (ch) { return ch.path === part.path; });
    if (i < 0) return;
    var prev = i > 0 ? guide.chapters[i - 1] : { url: guide.url, title: guide.title, front: true };
    var next = guide.chapters[i + 1];
    page.appendChild(el("nav", { class: "f-pager", "aria-label": "Chapters" }, [
      el("a", { class: "f-prev", href: href(prev.url) }, [el("small", { text: prev.front ? "Guide" : "Previous" }), el("span", { text: prev.title })]),
      next ? el("a", { class: "f-next", href: href(next.url) }, [el("small", { text: "Next" }), el("span", { text: next.title })]) : null
    ]));
  }

  /* --------------------------------------------------------- home page */
  function homeInbox() {
    var box = el("div", { class: "f-home-inbox" });
    page.insertBefore(box, main);
    optional(inboxLine(box), null);
  }
  function homeMaps() {
    var ids = ((D.site.home || {}).maps) || [];
    if (ids.length) {
      var grid = el("div", { class: "f-maps" });
      ids.forEach(function (id) {
        var map = byId(id).filter(function (d) { return d.rows; })[0];
        if (!map || !inFocus(map)) return;
        // The map's own row order, first rows shown.
        var rows = (map.rows || []).map(byKey).filter(function (d) { return d && d.status !== "draft" && inFocus(d); });
        var ul = el("ul");
        rows.slice(0, 5).forEach(function (d) {
          ul.appendChild(el("li", null, [el("a", { href: docURL(d), title: d.description, text: d.title }), el("span", { class: "f-genre", text: d.genre })]));
        });
        if (rows.length > 5) ul.appendChild(el("li", { class: "f-more", text: "and " + (rows.length - 5) + " more" }));
        grid.appendChild(el("div", { class: "f-map" }, [
          el("a", { href: docURL(map), text: map.title }),
          map.description ? el("p", { text: map.description }) : null,
          rows.length ? ul : null
        ]));
      });
      page.insertBefore(el("section", { class: "f-section f-home-maps", style: "margin-top:0;margin-bottom:2.5rem" },
        [el("h2", { text: "Maps" }), grid]), main);
    }
    optional(fetchJSON(".folio/journal.json"), []).then(function (entries) {
      entries = entries.filter(function (e) { return inFocus(byKey(e.path)); });
      if (!entries.length) return;
      var ul = el("ul", { class: "f-recent" });
      entries.slice(0, 4).forEach(function (e) {
        ul.appendChild(el("li", null, [el("time", { datetime: e.date, text: fmtDate(e.date) }),
          el("span", null, [el("a", { href: href(e.url), text: e.title }), e.kind ? " " : null,
            e.kind ? el("span", { class: "f-kind", "data-kind": e.kind, text: e.kind }) : null])]));
      });
      page.appendChild(el("section", { class: "f-section" }, [el("h2", { text: "Lately" }), ul,
        el("a", { class: "f-all", href: href((D.site.journal || {}).url || "/content/journal/"), text: "The whole journal" })]));
    });
  }

  /* ------------------------------------------------------ journal view */
  function journalView() {
    document.body.classList.add("f-journal");
    page.insertBefore(el("header", { class: "f-head" }, [
      el("div", { class: "f-eyebrow" }, [el("span", { text: "Journal" })]),
      el("h1", { class: "f-title", text: meta("title") || "Journal" }),
      el("p", { class: "f-sub", text: meta("description") })
    ]), main);
    panel.remove();
    document.body.classList.add("f-wide");
    fetchJSON(".folio/journal.json").then(function (entries) {
      entries = entries.filter(function (e) { return inFocus(byKey(e.path)); });
      if (focused()) main.appendChild(focusNote("journal entries"));
      var params = new URLSearchParams(location.search);
      var state = { kind: params.get("kind") || "", tag: params.get("tag") || "", about: params.get("about") || "",
                    since: params.get("since") || "", until: params.get("until") || "" };
      var kinds = {}, tags = {}, abouts = {};
      entries.forEach(function (e) {
        if (e.kind) kinds[e.kind] = (kinds[e.kind] || 0) + 1;
        (e.tags || []).forEach(function (t) { tags[t] = 1; });
        (e.about || []).forEach(function (a) { abouts[a] = 1; });
      });
      var filters = el("div", { class: "f-filters", role: "search" });
      var chips = el("div", { class: "f-chips", role: "group", "aria-label": "Kind" });
      function chip(kind, label, count) {
        return el("button", { type: "button", class: "f-chip", "data-kind": kind, "aria-pressed": String(state.kind === kind),
          onclick: function () { state.kind = kind; render(); } }, [label, count ? el("span", { class: "f-count", text: String(count) }) : null]);
      }
      chips.appendChild(chip("", "All", entries.length));
      Object.keys(kinds).sort().forEach(function (k) { chips.appendChild(chip(k, k, kinds[k])); });
      function select(name, label, values, describe) {
        var s = el("select", { name: name, onchange: function () { state[name] = s.value; render(); } },
          [el("option", { value: "", text: "Any" })]);
        values.sort().forEach(function (v) { s.appendChild(el("option", { value: v, text: describe ? describe(v) : v })); });
        s.value = state[name];
        return el("label", null, [label, s]);
      }
      function dateInput(name, label) {
        var i = el("input", { type: "date", name: name, value: state[name], onchange: function () { state[name] = i.value; render(); } });
        return el("label", null, [label, i]);
      }
      filters.appendChild(chips);
      filters.appendChild(select("tag", "Tag", Object.keys(tags)));
      filters.appendChild(select("about", "About", Object.keys(abouts), function (id) { var d = byId(id)[0]; return d ? d.title + " (" + d.genre + ")" : id; }));
      filters.appendChild(dateInput("since", "From"));
      filters.appendChild(dateInput("until", "To"));
      filters.appendChild(el("button", { type: "button", class: "f-chip f-reset", text: "Clear", onclick: function () {
        state = { kind: "", tag: "", about: "", since: "", until: "" };
        filters.querySelectorAll("select, input").forEach(function (x) { x.value = ""; });
        render();
      } }));
      var list = el("div", { class: "f-journal-list" });
      main.appendChild(filters);
      main.appendChild(list);

      function render() {
        Array.prototype.forEach.call(chips.children, function (c) { c.setAttribute("aria-pressed", String(c.getAttribute("data-kind") === state.kind)); });
        var q = new URLSearchParams();
        Object.keys(state).forEach(function (k) { if (state[k]) q.set(k, state[k]); });
        history.replaceState(null, "", location.pathname + (q.toString() ? "?" + q : ""));
        var shown = entries.filter(function (e) {
          return (!state.kind || e.kind === state.kind) && (!state.tag || (e.tags || []).indexOf(state.tag) >= 0) &&
            (!state.about || (e.about || []).indexOf(state.about) >= 0) &&
            (!state.since || e.date >= state.since) && (!state.until || e.date <= state.until);
        });
        list.textContent = "";
        if (!shown.length) { list.appendChild(el("p", { class: "f-empty", text: focused() ? "No entry in your focus matches these filters." : "No entry matches these filters." })); return; }
        var month = "", ol = null;
        shown.forEach(function (e) {
          var m = String(e.date).slice(0, 7);
          if (m !== month) {
            month = m;
            list.appendChild(el("h2", { class: "f-month", text: MONTHS[parseInt(m.slice(5), 10) - 1] + " " + m.slice(0, 4) }));
            ol = el("ol", { class: "f-timeline" });
            list.appendChild(ol);
          }
          var about = el("div", { class: "f-about" });
          (e.about || []).forEach(function (id) {
            var d = byId(id)[0];
            about.appendChild(d ? docChip(d) : el("span", { text: id }));
          });
          ol.appendChild(el("li", { class: "f-entry", "data-kind": e.kind || "" }, [
            el("div", { class: "f-entry-top" }, [el("time", { datetime: e.date, text: fmtDate(e.date) }),
              e.kind ? el("span", { class: "f-kind", "data-kind": e.kind, text: e.kind }) : null]),
            el("a", { href: href(e.url), text: e.title }),
            e.description ? el("p", { text: e.description }) : null,
            about.childNodes.length ? about : null
          ]));
        });
      }
      render();
    });
  }

  /* ------------------------------------------------------------ search */
  var palette, paletteInput, paletteList, paletteScope, selected = 0, searchAll = false;
  function loadSearch() {
    if (!D.search) D.search = fetchJSON(".folio/search.json");
    return D.search;
  }
  function buildPalette() {
    paletteInput = el("input", { type: "search", placeholder: "Search the library", "aria-label": "Search the library", autocomplete: "off" });
    paletteList = el("ol", { role: "listbox" });
    palette = el("div", { class: "f-palette", role: "dialog", "aria-modal": "true", "aria-label": "Search",
      onclick: function (e) { if (e.target === palette) closeSearch(); } }, [
      el("div", { class: "f-palette-box" }, [paletteInput, paletteScope = el("div", { class: "f-scope" }), paletteList,
        el("div", { class: "f-hint", text: "↑ ↓ to move · Enter to open · Esc to close" })])
    ]);
    paletteInput.addEventListener("input", runSearch);
    paletteInput.addEventListener("keydown", function (e) {
      var items = paletteList.children;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        selected = Math.max(0, Math.min(items.length - 1, selected + (e.key === "ArrowDown" ? 1 : -1)));
        mark();
      } else if (e.key === "Enter" && items[selected]) {
        e.preventDefault();
        location.href = items[selected].querySelector("a").href;
      } else if (e.key === "Escape") closeSearch();
    });
    document.body.appendChild(palette);
  }
  function mark() {
    Array.prototype.forEach.call(paletteList.children, function (li, i) {
      li.setAttribute("aria-selected", String(i === selected));
      if (i === selected) li.scrollIntoView({ block: "nearest" });
    });
  }
  function openSearch(query) {
    if (!palette) buildPalette();
    palette.setAttribute("data-open", "");
    paletteInput.value = typeof query === "string" ? query : "";
    searchAll = false;
    paletteInput.focus();
    loadSearch().then(runSearch);
  }
  function closeSearch() { if (palette) palette.removeAttribute("data-open"); }
  function highlight(text, words) {
    var span = el("em");
    var lower = text.toLowerCase(), at = -1, word = "";
    words.forEach(function (w) { var i = lower.indexOf(w); if (i >= 0 && (at < 0 || i < at)) { at = i; word = w; } });
    if (at < 0) { span.textContent = text.slice(0, 140); return span; }
    var start = Math.max(0, at - 50);
    span.appendChild(document.createTextNode((start ? "…" : "") + text.slice(start, at)));
    span.appendChild(el("b", { text: text.slice(at, at + word.length) }));
    span.appendChild(document.createTextNode(text.slice(at + word.length, at + word.length + 90) + "…"));
    return span;
  }
  function runSearch() {
    loadSearch().then(function (rows) {
      var words = paletteInput.value.toLowerCase().split(/\s+/).filter(Boolean);
      var scored = [], hidden = 0;
      paletteScope.textContent = "";
      if (focused()) [icon("focus"),
        el("span", { text: searchAll ? "Searching the whole library." : "Searching your focus: " + focusNames() + "." }),
        el("button", { type: "button", text: searchAll ? "Back to your focus" : "Search everything", onclick: function () {
          searchAll = !searchAll; runSearch(); paletteInput.focus(); } })].forEach(function (n) { paletteScope.appendChild(n); });
      rows.forEach(function (r) {
        if (focused() && !searchAll && !pathInFocus(r.path)) { hidden++; return; }
        var title = (r.title || "").toLowerCase(), desc = (r.description || "").toLowerCase();
        var tags = (r.tags || []).join(" ").toLowerCase(), text = (r.text || "").toLowerCase(), id = (r.id || "").toLowerCase();
        var score = 0;
        for (var i = 0; i < words.length; i++) {
          var w = words[i], s = 0;
          if (id === w) s += 12;
          if (title.indexOf(w) >= 0) s += title.indexOf(w) === 0 ? 8 : 5;
          if (desc.indexOf(w) >= 0) s += 3;
          if (tags.indexOf(w) >= 0) s += 3;
          if (text.indexOf(w) >= 0) s += 1;
          if (!s) return;
          score += s;
        }
        if (r.status === "draft" || r.status === "retired") score -= 1;
        if (r.genre === "journal") score -= 0.5;
        scored.push([words.length ? score : 0, r]);
      });
      if (!words.length) scored = scored.filter(function (s) { return s[1].genre === "map"; });
      scored.sort(function (a, b) { return b[0] - a[0]; });
      paletteList.textContent = "";
      selected = 0;
      scored.slice(0, 30).forEach(function (pair) {
        var r = pair[1];
        paletteList.appendChild(el("li", { role: "option" }, [el("a", { href: href(r.url) }, [
          el("span", { class: "f-genre", text: r.genre + (r.status && r.status !== "live" ? " · " + r.status : "") }),
          el("strong", { text: r.title }),
          r.description ? el("span", { text: r.description }) : null,
          words.length ? highlight(r.text || "", words) : null
        ])]));
      });
      if (!scored.length) paletteList.appendChild(el("li", null, [el("p", { class: "f-empty", style: "padding:.6rem .75rem;margin:0",
        text: hidden && words.length ? "Nothing in your focus matches." : "Nothing matches." })]));
      mark();
    });
  }
  document.addEventListener("keydown", function (e) {
    var typing = /INPUT|TEXTAREA|SELECT/.test((e.target || {}).tagName || "") || (e.target || {}).isContentEditable;
    if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) { e.preventDefault(); openSearch(); }
    else if (e.key === "/" && !typing) { e.preventDefault(); openSearch(); }
    else if (e.key === "[" && !typing && !e.metaKey && !e.ctrlKey && !e.altKey) { e.preventDefault(); setRail(!railShown()); }
    else if (e.key === "Escape") {
      if (narrow() && document.body.classList.contains("f-rail-open")) setRail(false);
      closeSearch(); hidePop();
    }
  });

  /* ----------------------------------------- previews and concept popovers */
  var pop = null, popTimer = null, defnCache = {};
  function hidePop() { if (pop) { pop.remove(); pop = null; } }
  function place(node, a) {
    document.body.appendChild(node);
    var r = a.getBoundingClientRect();
    var w = node.offsetWidth;
    var left = Math.max(12, Math.min(window.scrollX + r.left, window.scrollX + document.documentElement.clientWidth - w - 12));
    var below = r.bottom + node.offsetHeight + 16 < window.innerHeight;
    node.style.left = left + "px";
    node.style.top = (below ? window.scrollY + r.bottom + 8 : window.scrollY + r.top - node.offsetHeight - 8) + "px";
    node.addEventListener("mouseleave", hidePop);
  }
  function definition(info, a) {
    var url = a.href.split("#")[0];
    if (!defnCache[url]) defnCache[url] = fetch(url).then(function (r) { return r.text(); }).then(function (text) {
      var docu = new DOMParser().parseFromString(text, "text/html");
      var defn = docu.querySelector(".defn");
      if (!defn) return "";
      var name = defn.querySelector(".defn-name");
      if (name) name.remove();
      return defn.textContent.replace(/\s+/g, " ").trim();
    });
    return defnCache[url];
  }
  function showPreview(a) {
    var info = lookupHref(a);
    if (!info) return;
    var doc = info.doc, target = info.part || doc;
    var isDefn = a.classList.contains("defn-link");
    var box = el("div", { class: "f-pop" + (isDefn ? " f-defn" : ""), role: "tooltip" }, [
      el("span", { class: "f-genre", text: doc.genre + (doc.status && doc.status !== "live" ? " · " + doc.status : "") }),
      el("strong", { text: target.title }),
      el("p", { text: target.description })
    ]);
    hidePop();
    pop = box;
    place(box, a);
    if (isDefn) definition(info, a).then(function (text) {
      // The definition is longer than the description: place the popover again for its new height.
      if (text && pop === box) { box.querySelector("p").textContent = text; place(box, a); }
    });
  }
  function hookPreviews(root) {
    root.addEventListener("mouseover", function (e) {
      var a = e.target.closest && e.target.closest("a[href]");
      if (!a || a.closest(".f-pop") || a.closest(".f-palette") || a.closest(".f-top")) return;
      clearTimeout(popTimer);
      popTimer = setTimeout(function () { showPreview(a); }, a.classList.contains("defn-link") ? 150 : 400);
    });
    root.addEventListener("mouseout", function (e) {
      var a = e.target.closest && e.target.closest("a[href]");
      if (!a) return;
      clearTimeout(popTimer);
      setTimeout(function () { if (pop && !pop.matches(":hover")) hidePop(); }, 200);
    });
    root.addEventListener("focusin", function (e) {
      var a = e.target.closest && e.target.closest("a.defn-link");
      if (a) showPreview(a);
    });
    root.addEventListener("focusout", hidePop);
  }

  /* ------------------------------------------------------- comments */
  // Served by `folio serve`, the site says whether this reader may comment (D.site.comments).
  // An exported site has no server: the panel says where comments are open, and nothing more.
  var API = BASE + "_folio/annotations";
  var INBOX = BASE + "_folio/inbox";
  var STATIC_LINE = "Comments are open where this library is served with folio serve.";
  function served() { return !!D.site.comments; }
  function reviewURL() { return href(((D.site.review || {}).url) || "/content/review/"); }
  // The file keeps five states; a reader sees three words, and how a closed thread closed.
  function stateChip(t) {
    var word = t.word || (t.state === "open" ? "waiting" : t.state === "noted" ? "resting" : "closed");
    var text = word === "closed" && t.how ? "closed · " + t.how : word;
    return el("span", { class: "f-cstate", "data-w": word, "data-how": t.how || null, text: text });
  }
  function postJSON(body) {
    return fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) throw new Error(j.error || ("The server answered " + r.status));
          return j;
        });
      });
  }
  function staticNote() {
    panelSection("Comments", el("p", { class: "f-cnote", text: STATIC_LINE }));
  }
  function whatChanged(c) {
    function side(label, part, cls) {
      return el("div", { class: "f-side" }, [el("span", { text: label }),
        el("p", null, [part.lead ? part.lead + " " : "", el(cls, { text: part.text || "(nothing)" }), part.tail ? " " + part.tail : ""])]);
    }
    return el("div", { class: "f-changed" }, [
      el("div", { class: "f-changed-head", text: "What changed" }),
      side("Before", c.before, "del"),
      side("After", c.after, "ins")
    ]);
  }

  function annotations(rel) {
    var status = D.site.comments;
    var source = rel;
    var info = lookup(rel);
    if (info) source = (info.part || info.doc).path;
    var threads = [];
    var fab = el("button", { class: "f-anno-fab", type: "button", "aria-label": "Comments", onclick: function () { openDrawer(); } }, [icon("chat")]);
    document.body.classList.add("f-live");
    var list = el("div", { class: "f-threads" });
    var drawer = el("aside", { class: "f-drawer", "aria-label": "Comments" }, [
      el("header", null, [el("h2", { text: "Comments on this page" }),
        el("button", { class: "f-btn", type: "button", "aria-label": "Close", onclick: function () { drawer.removeAttribute("data-open"); } }, [icon("close")])]),
      list
    ]);
    var ask = el("button", { class: "f-anno-ask", type: "button", text: "Comment" });
    var pendingQuote = null;  // null: not writing; "": a comment on the whole page; else the passage
    var changing = null;      // the id of a resting flag whose Change form is open
    document.body.appendChild(fab);
    document.body.appendChild(drawer);

    function load() {
      return fetch(API + "?doc=" + encodeURIComponent(source)).then(function (r) { return r.json(); }).then(function (j) {
        threads = j.threads || [];
        render();
      });
    }
    function send(data, error) {
      data.doc = source;
      return postJSON(data).then(load).catch(function (err) { error.textContent = err.message; throw err; });
    }
    function form(fields, label, submit) {
      var error = el("p", { class: "f-error", role: "alert" });
      var f = el("form", { class: "f-form" }, fields.concat([error, el("button", { type: "submit", text: label || "Send" })]));
      f.addEventListener("submit", function (e) {
        e.preventDefault();
        var data = {};
        Array.prototype.forEach.call(f.elements, function (x) {
          if (!x.name) return;
          data[x.name] = x.type === "checkbox" ? x.checked : x.value;
        });
        submit(data, error).catch(function () {});
      });
      return f;
    }
    function render() {
      var waiting = threads.filter(function (t) { return t.state === "open"; }).length;
      fab.textContent = "";
      fab.appendChild(icon("chat"));
      fab.appendChild(el("span", { class: "f-label", text: "Comments" }));
      if (waiting) fab.appendChild(el("span", { class: "f-count", title: waiting + " waiting", text: String(waiting) }));
      list.textContent = "";
      if (!status.open) {
        list.appendChild(el("p", { class: "f-cnote f-readonly", text: status.reason || "Comments are read-only here." }));
      } else if (pendingQuote === null) {
        list.appendChild(el("div", { class: "f-cwho" }, [
          el("span", { text: "Commenting as " }), el("strong", { text: status.who }),
          el("button", { class: "f-btn f-whole-btn", type: "button", text: "Comment on the whole page",
            onclick: function () { pendingQuote = ""; render(); } })]));
      } else {
        list.appendChild(el("div", { class: "f-thread f-new" }, [el("strong", { text: "New comment" }),
          pendingQuote ? el("blockquote", { text: pendingQuote }) : el("p", { class: "f-whole", text: "About the whole page" }),
          form([
            el("select", { name: "kind", "aria-label": "Kind" }, [el("option", { value: "question", text: "Question" }), el("option", { value: "flag", text: "Flag" })]),
            el("textarea", { name: "body", placeholder: "What should change, or what do you want to know?", required: true })
          ], "Send", function (data, error) {
            data.action = "add"; data.quote = pendingQuote;
            return send(data, error).then(function () { pendingQuote = null; render(); });
          }),
          el("button", { class: "f-btn", type: "button", text: "Cancel", onclick: function () { pendingQuote = null; render(); } })]));
      }
      if (!threads.length && pendingQuote === null)
        list.appendChild(el("p", { class: "f-empty", text: status.open ? "No comments yet. Select a passage to ask about it, or comment on the whole page." : "No comments on this page." }));
      threads.slice().reverse().forEach(function (t) { list.appendChild(threadBox(t)); });
      highlightQuotes();
    }
    function threadBox(t) {
      var box = el("div", { class: "f-thread", id: "comment-" + t.id, "data-w": t.word || null }, [
        el("div", { class: "f-entry-top" }, [el("span", { class: "f-kind", text: t.kind }),
          t.label ? el("span", { text: t.label }) : null, stateChip(t)]),
        t.quote ? el("blockquote", { text: t.quote }) : el("p", { class: "f-whole", text: "About the whole page" })
      ]);
      var was = t.kind === "flag" ? "noted" : "open";
      var MOVES = { open: "reopened", noted: "rested", declined: "declined", withdrawn: "withdrew" };
      (t.messages || []).forEach(function (m, i) {
        var moved = "";
        if (i && m.state) {
          moved = m.state === "addressed" ? (was === "noted" ? "kept" : "changed") : MOVES[m.state] || m.state;
          was = m.state;
        }
        box.appendChild(el("div", { class: "f-msg" }, [el("small", { text: m.author + " · " + fmtDate(m.date) + (moved ? " · " + moved : "") }),
          el("p", { text: m.body })]));
      });
      if (t.changed) box.appendChild(whatChanged(t.changed));
      if (!status.open) return box;
      if (t.author === status.who) {
        var delError = el("p", { class: "f-error", role: "alert" });
        box.appendChild(el("div", { class: "f-thread-tools" }, [
          el("button", { class: "f-btn f-delete", type: "button", text: "Delete", title: "Delete this thread; git keeps the history",
            onclick: function () {
              if (!window.confirm("Delete this comment thread? It disappears from the page; the commit history keeps it.")) return;
              send({ action: "delete", id: t.id }, delError).catch(function () {});
            } }), delError]));
      }
      if (t.kind === "flag" && t.state === "noted") {
        var error = el("p", { class: "f-error", role: "alert" });
        if (changing === t.id) {
          box.appendChild(form([el("textarea", { name: "body", placeholder: "What should change?", required: true })], "Ask for the change",
            function (data, err) { data.action = "change"; data.id = t.id; return send(data, err).then(function () { changing = null; render(); }); }));
          box.appendChild(el("button", { class: "f-btn", type: "button", text: "Cancel", onclick: function () { changing = null; render(); } }));
        } else {
          box.appendChild(el("div", { class: "f-choice" }, [
            el("button", { class: "f-keep", type: "button", text: "Keep", title: "Keep the passage as it is; the flag closes",
              onclick: function () { send({ action: "keep", id: t.id }, error).catch(function () {}); } }),
            el("button", { class: "f-change", type: "button", text: "Change", title: "Say what to change; the agent picks it up",
              onclick: function () { changing = t.id; render(); } })]));
          box.appendChild(error);
        }
        return box;
      }
      var closed = t.state !== "open" && t.state !== "noted";
      box.appendChild(form([
        el("textarea", { name: "body", placeholder: closed ? "Reply, or reopen with what is still wrong" : "Reply", required: true }),
        closed ? el("label", { class: "f-reopen" }, [el("input", { type: "checkbox", name: "reopen" }), " Reopen"]) : null
      ], "Reply", function (data, err) { data.action = "reply"; data.id = t.id; return send(data, err); }));
      return box;
    }
    function highlightQuotes() {
      Array.prototype.forEach.call(main.querySelectorAll("mark.f-anno"), function (m) {
        m.replaceWith(document.createTextNode(m.textContent));
      });
      main.normalize();
      threads.forEach(function (t) {
        if (!t.quote || t.state === "withdrawn") return;
        var walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT);
        var node;
        while ((node = walker.nextNode())) {
          var i = node.nodeValue.indexOf(t.quote);
          if (i < 0) continue;
          var range = document.createRange();
          range.setStart(node, i); range.setEnd(node, i + t.quote.length);
          var m = el("mark", { class: "f-anno", "data-w": t.word || null, title: t.kind + ": " + (t.word || t.state) });
          m.addEventListener("click", function () { openDrawer(t.id); });
          range.surroundContents(m);
          break;
        }
      });
    }
    function openDrawer(id) {
      drawer.setAttribute("data-open", "");
      render();
      if (id) {
        var t = document.getElementById("comment-" + id);
        if (t) { t.scrollIntoView({ block: "start" }); t.classList.add("f-focus"); }
      }
    }
    if (status.open) document.addEventListener("mouseup", function () {
      setTimeout(function () {
        var sel = window.getSelection();
        var text = sel ? sel.toString().trim() : "";
        if (!text || !main.contains(sel.anchorNode)) { ask.remove(); return; }
        var r = sel.getRangeAt(0).getBoundingClientRect();
        ask.style.left = (window.scrollX + r.left) + "px";
        ask.style.top = (window.scrollY + r.top - 36) + "px";
        ask.onclick = function () { pendingQuote = text.replace(/\s+/g, " "); ask.remove(); openDrawer(); };
        document.body.appendChild(ask);
      }, 0);
    });
    load().then(function () {
      var m = /^#comment-(.+)$/.exec(location.hash);
      if (m) openDrawer(decodeURIComponent(m[1]));
    });
  }

  /* -------------------------------------------------------- review page */
  /* The inbox, narrowed to the focus: its threads, and its counts taken again. */
  function focusInbox(j) {
    if (!focused()) return j;
    var threads = (j.threads || []).filter(function (t) { return pathInFocus(t.path); });
    return { threads: threads,
      waiting: threads.filter(function (t) { return t.state === "open"; }).length,
      resting: threads.filter(function (t) { return t.state === "noted"; }).length };
  }
  function focusNote(what) {
    return el("p", { class: "f-outside f-focus-note" }, [icon("focus"),
      el("span", { text: "Showing the " + what + " in your focus on " + focusNames() + "." }), clearFocusButton("Show all")]);
  }
  function inboxLine(box) {
    return fetch(INBOX).then(function (r) { return r.json(); }).then(focusInbox).then(function (j) {
      var q = j.waiting === 1 ? "1 question" : j.waiting + " questions";
      var f = j.resting === 1 ? "1 flag" : j.resting + " flags";
      var text = j.waiting || j.resting ? q + " waiting on the agent, " + f + " for you" : "Nothing waiting: no open questions, no resting flags";
      if (focused()) text += ", in your focus";
      box.appendChild(el("a", { class: "f-inbox-line", href: reviewURL() }, [icon("chat"), el("span", { text: text })]));
      return j;
    });
  }
  function reviewView() {
    document.body.classList.add("f-journal", "f-review");
    page.insertBefore(el("header", { class: "f-head" }, [
      el("div", { class: "f-eyebrow" }, [el("span", { text: "Review" })]),
      el("h1", { class: "f-title", text: meta("title") || "Review" }),
      el("p", { class: "f-sub", text: meta("description") })
    ]), main);
    panel.remove();
    document.body.classList.add("f-wide");
    if (!served()) { main.appendChild(el("p", { class: "f-cnote", text: STATIC_LINE })); return; }
    fetch(INBOX).then(function (r) { return r.json(); }).then(focusInbox).then(function (j) {
      if (focused()) main.appendChild(focusNote("comments"));
      var shown = "";
      var chips = el("div", { class: "f-chips", role: "group", "aria-label": "Show" });
      function chip(value, label, count) {
        return el("button", { type: "button", class: "f-chip", "data-v": value, "aria-pressed": String(shown === value),
          onclick: function () { shown = value; render(); } }, [label, el("span", { class: "f-count", text: String(count) })]);
      }
      chips.appendChild(chip("", "All", j.threads.length));
      chips.appendChild(chip("open", "Waiting on the agent", j.waiting));
      chips.appendChild(chip("noted", "Flags for you", j.resting));
      var list = el("ol", { class: "f-inbox" });
      main.appendChild(el("div", { class: "f-filters" }, [chips]));
      main.appendChild(list);
      function render() {
        Array.prototype.forEach.call(chips.children, function (c) { c.setAttribute("aria-pressed", String(c.getAttribute("data-v") === shown)); });
        list.textContent = "";
        var rows = j.threads.filter(function (t) { return !shown || t.state === shown; });
        if (!rows.length) { list.appendChild(el("li", { class: "f-empty", text: "Nothing here." })); return; }
        rows.forEach(function (t) {
          var link = href(t.url) + "#comment-" + encodeURIComponent(t.id);
          var mine = t.state === "noted";
          list.appendChild(el("li", { class: "f-inbox-row", "data-w": t.word }, [
            el("div", { class: "f-entry-top" }, [
              el("time", { datetime: t.last.date || t.created, text: fmtDate(t.last.date || t.created) }),
              el("span", { class: "f-kind", text: t.kind }), t.label ? el("span", { text: t.label }) : null,
              stateChip(t),
              el("span", { class: "f-who", text: mine ? "for you" : "waiting on the agent" })]),
            el("div", null, [t.genre ? el("span", { class: "f-genre", text: t.genre }) : null,
              el("a", { class: "f-inbox-doc", href: link, text: t.title })]),
            t.quote ? el("blockquote", { text: t.quote }) : el("p", { class: "f-whole", text: "About the whole page" }),
            el("p", { class: "f-inbox-msg" }, [el("strong", { text: (t.last.author || t.author) + ": " }), t.last.body || ""]),
            el("a", { class: "f-inbox-go", href: link, text: mine ? "Keep or change it on the page" : "Open the passage" })
          ]));
        });
      }
      render();
    }).catch(function (err) { main.appendChild(el("p", { class: "f-error", text: err.message })); });
  }

  /* ---------------------------------------------------------------- math */
  /* KaTeX, vendored beside this script, on a page with <meta name="math">. It typesets $…$, $$…$$,
     \(…\) and \[…\] inside <main>, never in code, scripts or a definition's name. */
  function loadMath() {
    var dir = BASE + "shell/vendor/katex/";
    function add(tag, attrs) {
      return new Promise(function (done, fail) {
        var n = el(tag, attrs);
        n.onload = done;
        n.onerror = function () { fail(new Error("could not load " + (attrs.src || attrs.href))); };
        if (tag === "script") n.async = false;  // in order: auto-render needs katex
        document.head.appendChild(n);
      });
    }
    return Promise.all([
      add("link", { rel: "stylesheet", href: dir + "katex.min.css" }),
      add("script", { src: dir + "katex.min.js" }),
      add("script", { src: dir + "contrib/auto-render.min.js" })
    ]);
  }
  function typeset() {
    window.renderMathInElement(main, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false }
      ],
      throwOnError: false,
      ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code"],
      ignoredClasses: ["defn-name"]
    });
  }

  /* KaTeX's common faces, fetched before the page shows so the math does not change face after it;
     a slow font is not waited for longer than half a second. */
  function mathFonts() {
    if (!document.fonts || !document.fonts.load) return null;
    var faces = ["1em KaTeX_Main", "italic 1em KaTeX_Main", "italic 1em KaTeX_Math"];
    return Promise.race([
      Promise.all(faces.map(function (f) { return document.fonts.load(f); })),
      new Promise(function (done) { setTimeout(done, 500); })
    ]);
  }

  /* --------------------------------------------------------------- start */
  function start() {
    var view = meta("folio-view");
    var rel = meta("folio-source") || relOf(location.pathname);
    if (view || meta("layout") === "column") document.body.classList.add("f-column");
    // KaTeX loads beside the indices, and the page shows once its math is set, not before.
    var math = document.querySelector('meta[name="math"]') ? loadMath() : null;
    Promise.all([
      optional(fetchJSON(".folio/catalog.json"), { documents: [] }),
      optional(fetchJSON(".folio/backlinks.json"), {}),
      optional(fetchJSON(".folio/nav.json"), {}),
      optional(fetchJSON(".folio/site.json"), {})
    ]).then(function (all) {
      index(all[0]);
      D.backlinks = all[1]; D.nav = all[2]; D.site = all[3];
      loadFocus();
      frame(view, rel);
      if (view === "journal") { journalView(); }
      else if (view === "review") { reviewView(); }
      else {
        var info = lookup(rel);
        header(info);
        if (info) {
          var doc = info.doc, links = D.backlinks[doc.path] || {};
          banners(doc, links);
          mapRows();
          if (doc.id === "home") { if (served()) homeInbox(); homeMaps(); }
          if (doc.versions) paperLanding(doc);
          guideNav(doc, info.part && info.part.number ? info.part : null);
          outline();
          linkPanels(doc, links);
          detailsPanel(doc, (info.part || doc).path);
        } else {
          mapRows();
          outline();
        }
        if (served()) { if (info) annotations(rel); }
        else if (info) staticNote();
        if (!panel.childNodes.length) { panel.remove(); document.body.classList.add("f-wide"); }
      }
      hookPreviews(document.body);
      figures();
      return math && math.then(typeset).then(mathFonts);
    }).catch(function (err) {
      if (window.console) console.error("folio:", err);
    }).then(function () {
      document.documentElement.classList.add("f-ready");  // the stylesheet shows the page now, drawn or not
      // The browser jumped to the address's #section while the page was hidden and undrawn; jump again now.
      var target = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (target) target.scrollIntoView();
    });
    prerenderLinks();
  }

  /* ------------------------------------------------------------ figures */
  /* An inline SVG is drawn for a size: its viewBox. Stretched across a wide canvas its labels grow
     with it, so each one is held near that size (a page opts out with data-fit="wide" on the figure
     or the svg). Every figure can also be opened larger, in a dialog: the figure itself moves into
     it and back, so its controls keep working (data-expand="no" leaves a figure out). */
  var FIT = 1.15;
  function figures() {
    Array.prototype.forEach.call(document.querySelectorAll("main figure"), function (fig) {
      if (fig.parentNode.closest && fig.parentNode.closest("figure")) return;  // a figure inside a figure
      Array.prototype.forEach.call(fig.querySelectorAll("svg[viewBox]"), function (svg) {
        if (fig.getAttribute("data-fit") === "wide" || svg.getAttribute("data-fit") === "wide") return;
        if (svg.closest("button, a")) return;
        var box = (svg.getAttribute("viewBox") || "").trim().split(/[\s,]+/).map(Number);
        if (box.length === 4 && box[2] > 48) svg.style.maxWidth = Math.round(box[2] * FIT) + "px";
      });
      if (fig.getAttribute("data-expand") === "no") return;
      fig.classList.add("f-fig");
      fig.appendChild(el("button", { class: "f-fig-expand", type: "button", "aria-label": "Open the figure larger",
        title: "Open larger", onclick: function () { openFigure(fig); } }, [icon("expand")]));
    });
  }
  function openFigure(fig) {
    /* The dialog sits where the figure was, so the page's own styles still reach it; showModal lifts it
       above the page whatever its ancestors. */
    var dialog = el("dialog", { class: "f-fig-dialog", "aria-label": fig.getAttribute("aria-label") || "Figure" });
    var shut = el("button", { class: "f-fig-close", type: "button", "aria-label": "Close", title: "Close (Esc)" }, [icon("close")]);
    fig.parentNode.insertBefore(dialog, fig);
    dialog.appendChild(shut);
    dialog.appendChild(fig);
    shut.addEventListener("click", function () { dialog.close(); });
    dialog.addEventListener("click", function (e) { if (e.target === dialog) dialog.close(); });
    dialog.addEventListener("close", function () {
      held.forEach(function (svg) { svg.style.minWidth = ""; svg.style.maxHeight = ""; });
      dialog.parentNode.insertBefore(fig, dialog);
      dialog.remove();
      var back = fig.querySelector(".f-fig-expand");
      if (back) back.focus({ preventScroll: true });
    });
    dialog.showModal();
    /* On a narrow screen the dialog would shrink a wide drawing again: show it at its drawn width
       instead, and let the dialog scroll sideways. */
    var held = [];
    Array.prototype.forEach.call(fig.querySelectorAll("svg[viewBox]"), function (svg) {
      var box = (svg.getAttribute("viewBox") || "").trim().split(/[\s,]+/).map(Number);
      if (box.length === 4 && box[2] > dialog.clientWidth) {
        svg.style.minWidth = Math.round(box[2]) + "px";
        svg.style.maxHeight = "none";
        held.push(svg);
      }
    });
    shut.focus();
  }

  /* Where the browser can, a page linked from this one is prepared while the pointer rests on its link,
     script and all, so following the link shows it at once. Others ignore the rules. */
  function prerenderLinks() {
    if (!(HTMLScriptElement.supports && HTMLScriptElement.supports("speculationrules"))) return;
    var rules = el("script", { type: "speculationrules" });
    rules.textContent = JSON.stringify({ prerender: [{
      where: { and: [{ href_matches: BASE + "*" }, { not: { href_matches: BASE + "_folio/*" } }] },
      eagerness: "moderate"
    }] });
    document.head.appendChild(rules);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
