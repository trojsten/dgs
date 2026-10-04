/*
 * Typeset maths once, at build time, so the page ships finished SVG and needs no JavaScript.
 *
 * The alternative was MathJax in the browser, and it does not survive the thing the pages are
 * for: Firefox gives every `file://` document its own origin, so MathJax's dynamic loads are
 * refused and a page opened from a directory shows `\(1.8\,\mathrm{m}\)` as text. Online it
 * looked right only because MathJax fell through to the CDN.
 *
 * Reads `{"font": "...", "items": [{"tex": "...", "display": false}, ...]}` on stdin and writes
 * the SVG strings back as JSON, in order. One process per page rather than per formula.
 *
 * **The font is chosen by loading its component, not by naming it.** `loader.font`, `svg.font`
 * and `output.font` are all accepted in silence and all do nothing here -- every spelling gives
 * byte-identical glyph paths. Loading `[font]/svg.js` with `paths` pointing at the package is
 * what actually changes the type.
 */
'use strict';

const path = require('path');

function read() {
    return new Promise((resolve, reject) => {
        let buffer = '';
        process.stdin.setEncoding('utf8');
        process.stdin.on('data', (chunk) => { buffer += chunk; });
        process.stdin.on('end', () => {
            try {
                resolve(JSON.parse(buffer));
            } catch (error) {
                reject(error);
            }
        });
        process.stdin.on('error', reject);
    });
}

(async () => {
    const request = await read();
    const font = request.font || '@mathjax/mathjax-pagella-font';
    const fontDirectory = path.dirname(require.resolve(`${font}/package.json`));

    const MathJax = await require('mathjax').init({
        loader: {
            load: ['input/tex', 'output/svg', '[tex]/mhchem', '[font]/svg.js'],
            paths: {font: fontDirectory},
        },
        tex: {
            packages: {'[+]': ['mhchem']},
            // `\(`/`\[` are pandoc's delimiters; the fragments arrive already stripped of them
            inlineMath: [['\\(', '\\)']],
            displayMath: [['\\[', '\\]']],
        },
        // `local` keeps each formula's glyph definitions inside its own `<svg>`, so a fragment
        // can be moved between pages without carrying a shared cache with it
        svg: {fontCache: 'local'},
    });

    const adaptor = MathJax.startup.adaptor;
    // `tex2svgPromise`, not `tex2svg`. A formula whose glyphs or extensions are not loaded yet
    // makes the synchronous call throw `MathJax retry -- an asynchronous action is required`,
    // and which formulas those are depends on what came before them in the batch: the first
    // page built clean and the second did not.
    const out = [];
    for (const item of request.items) {
        try {
            const node = await MathJax.tex2svgPromise(item.tex, {display: !!item.display});
            out.push({svg: adaptor.outerHTML(node)});
        } catch (error) {
            out.push({error: error.message});
        }
    }
    process.stdout.write(JSON.stringify(out));
})().catch((error) => {
    process.stderr.write(`mathjax-render: ${error.message}\n`);
    process.exit(1);
});
