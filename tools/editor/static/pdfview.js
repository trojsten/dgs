/* The PDF preview, drawn by pdf.js into the page rather than handed to the browser's viewer.

   The browser's viewer owns its own zoom and scroll, and gives neither back: Chrome's is a plugin
   the page cannot read at all, and every reload or change of `src` resets both. That made the
   preview useless for the one thing it is for -- recompiling and looking at the same spot again,
   or flipping a problem between languages to compare them. Drawing the pages ourselves means the
   editor holds the zoom and the scroll offset, so a recompile or a language switch keeps both.

   pdf.js is vendored under `vendor/pdfjs/` (pdfjs-dist 6.3.289, Apache-2.0), so the editor still
   works offline. There is no text layer: this is a preview to look at, and "open in tab" gives
   the browser's own viewer when text needs selecting. */

import * as pdfjs from "./vendor/pdfjs/pdf.min.mjs";

pdfjs.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.min.mjs";

const ZOOM_KEY = "dgs-editor-pdf-zoom";
const CSS_PER_PT = 96 / 72;          // what pdf.js's own viewer calls 100 %: true size on screen
const STEP = 1.2;
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 6;
const GAP = 12;                      // px between pages, and around them

function loadZoom() {
  try {
    const saved = localStorage.getItem(ZOOM_KEY);
    if (saved === "fit") return "fit";
    const n = parseFloat(saved);
    return Number.isFinite(n) ? n : "fit";
  } catch {
    return "fit";
  }
}

function saveZoom(zoom) {
  try { localStorage.setItem(ZOOM_KEY, String(zoom)); } catch { /* a convenience, not state */ }
}

export class PdfView {
  constructor(scroller, label) {
    this.scroller = scroller;      // the element that scrolls; the pages go inside it
    this.label = label;            // where the zoom percentage is shown
    this.zoom = loadZoom();        // a factor, or "fit" for the pane's width
    this.doc = null;
    this.url = null;
    this.generation = 0;           // bumped by every load/draw, so a slow one cannot land late

    scroller.addEventListener("wheel", (e) => {
      if (!e.ctrlKey) return;      // a plain wheel scrolls; Ctrl+wheel zooms, as in every viewer
      e.preventDefault();
      this.zoomBy(e.deltaY < 0 ? STEP : 1 / STEP);
    }, { passive: false });

    // Only "fit" depends on the pane's width, and dragging the column gutter changes it.
    let resizeTimer = null;
    new ResizeObserver(() => {
      if (this.zoom !== "fit" || !this.doc) return;
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => this.draw({ anchor: "keep" }), 150);
    }).observe(scroller);
  }

  /** The scale pdf.js is given for `page`, from the zoom setting. */
  scaleFor(page) {
    if (this.zoom !== "fit") return this.zoom * CSS_PER_PT;
    const width = page.getViewport({ scale: 1 }).width;
    return Math.max((this.scroller.clientWidth - 2 * GAP) / width, 0.1);
  }

  /** The effective zoom as a factor, so "fit" can be stepped from like any other value. */
  currentFactor() {
    if (this.zoom !== "fit" || !this.firstPage) return this.zoom === "fit" ? 1 : this.zoom;
    return this.scaleFor(this.firstPage) / CSS_PER_PT;
  }

  zoomBy(factor) {
    const next = Math.min(Math.max(this.currentFactor() * factor, MIN_ZOOM), MAX_ZOOM);
    this.setZoom(Math.round(next * 100) / 100);
  }

  setZoom(zoom) {
    this.zoom = zoom;
    saveZoom(zoom);
    if (this.doc) this.draw({ anchor: "centre" });
    else this.showLabel();
  }

  showLabel() {
    if (!this.label) return;
    this.label.textContent = this.zoom === "fit" && !this.firstPage ? "fit"
      : `${Math.round(this.currentFactor() * 100)} %`;
  }

  /** Fetch `url` and draw it, keeping the zoom and the scroll offset of whatever was shown. */
  async load(url) {
    const generation = ++this.generation;
    // It is the loading task that owns the worker's copy of a document, not the document.
    const task = pdfjs.getDocument({ url: url.split("#")[0], isEvalSupported: false });
    const doc = await task.promise;
    if (generation !== this.generation) { task.destroy(); return; }
    const old = this.task;
    this.task = task;
    this.doc = doc;
    this.url = url;
    this.firstPage = await doc.getPage(1);
    await this.draw({ anchor: "keep", generation });
    if (old) old.destroy();
  }

  /**
   * Empty the pane, for a language or a problem with nothing compiled yet. The scroll offset is
   * kept, so that compiling it lands where the previous document was being read.
   */
  clear() {
    this.generation++;
    this.remember();
    if (this.task) this.task.destroy();
    this.task = null;
    this.doc = null;
    this.url = null;
    this.firstPage = null;
    this.scroller.replaceChildren();
  }

  /** Note where the pane is scrolled, while there is still something in it to be scrolled. */
  remember() {
    if (!this.scroller.firstChild) return;
    this.top = this.scroller.scrollTop;
    this.left = this.scroller.scrollLeft;
  }

  /**
   * Draw every page into a fresh container and swap it in whole, so nothing flickers.
   *
   * `anchor` says which scroll position survives. "keep" is the same offset from the top, which
   * is what a recompile and a language switch want: the translation's layout is nearly the
   * same, so the same spot on the page is the same passage. "centre" keeps the point in the
   * middle of the pane where it is, which is what a zoom wants.
   */
  async draw({ anchor, generation = ++this.generation }) {
    const doc = this.doc;
    const ratio = window.devicePixelRatio || 1;
    const pages = document.createElement("div");
    pages.className = "pdf-pages";
    pages.style.padding = `${GAP}px`;

    for (let n = 1; n <= doc.numPages; n++) {
      const page = await doc.getPage(n);
      if (generation !== this.generation) return;
      const viewport = page.getViewport({ scale: this.scaleFor(page) });
      const canvas = document.createElement("canvas");
      canvas.width = Math.floor(viewport.width * ratio);
      canvas.height = Math.floor(viewport.height * ratio);
      canvas.style.width = `${Math.floor(viewport.width)}px`;
      canvas.style.height = `${Math.floor(viewport.height)}px`;
      canvas.style.marginBottom = `${GAP}px`;
      await page.render({
        canvas,
        canvasContext: canvas.getContext("2d"),
        viewport,
        transform: ratio === 1 ? null : [ratio, 0, 0, ratio, 0, 0],
      }).promise;
      if (generation !== this.generation) return;
      pages.appendChild(canvas);
    }

    const s = this.scroller;
    this.remember();
    const top = this.top ?? 0, left = this.left ?? 0;
    const centreY = s.scrollHeight ? (top + s.clientHeight / 2) / s.scrollHeight : 0;
    const centreX = s.scrollWidth ? (left + s.clientWidth / 2) / s.scrollWidth : 0.5;
    s.replaceChildren(pages);
    if (anchor === "centre") {
      s.scrollTop = centreY * s.scrollHeight - s.clientHeight / 2;
      s.scrollLeft = centreX * s.scrollWidth - s.clientWidth / 2;
    } else {
      s.scrollTop = top;
      s.scrollLeft = left;
    }
    this.showLabel();
  }
}
