/*
 * Put the font package where MathJax looks for its dynamic parts.
 *
 * A font's glyphs are split into chunks -- `latin.js`, `arrows.js`, `greek.js` -- loaded on
 * demand when a formula first needs one. Loading the font *component* from an arbitrary path
 * works, and the chunks are not resolved against that path: MathJax asks for
 * `[mathjax]/output/fonts/<name>/svg/dynamic/<chunk>.js` regardless. So a formula with no
 * `\text{}` in it typesets and one with `\text{voda}` fails, which is a confusing way to find
 * this out.
 *
 * npm runs this after install; `npm ci` recreates the link with the rest of node_modules.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const FONTS = {'mathjax-pagella': '@mathjax/mathjax-pagella-font'};

const root = path.join(__dirname, '..', '..', 'node_modules');
const target = path.join(root, 'mathjax', 'output', 'fonts');
fs.mkdirSync(target, {recursive: true});

for (const [name, pkg] of Object.entries(FONTS)) {
    const link = path.join(target, name);
    const source = path.relative(target, path.join(root, pkg));
    try {
        fs.unlinkSync(link);
    } catch { /* not there yet */ }
    fs.symlinkSync(source, link, 'dir');
    process.stdout.write(`${name} -> ${source}\n`);
}
