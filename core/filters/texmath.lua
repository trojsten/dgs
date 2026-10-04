--[[
Maths that is not really maths: rendered by LaTeX, dropped into the page as a picture.

MathJax covers ordinary LaTeX, has an mhchem extension for `\ce`, and `siunitx.lua` next door
deals with the units. What is left over is **chemfig**, which is TikZ in a lab coat -- 84
fragments in `chem/01` alone -- and for which no web implementation exists at all.

Approximating those would be the wrong trade. `core/templates/standalone.jtex` already loads
chemfig, mhchem, chemmacros, `math.tex` and `siunitx.tex`, and `dvisvgm` already turns the PDF
into an SVG, so the browser can have the drawing the booklet has rather than something like it.

**This runs before `siunitx.lua`**, so a fragment on its way to LaTeX still carries its original
`\qty`, which LaTeX can set and the rewriting could only spoil. Once it is an `Image`, the
siunitx filter no longer sees it.

The cache is content-addressed and shared: `core/html/mathimage.py` names a fragment by the hash
of itself, so an unchanged formula is never re-rendered, and the same formula written in two
problems is one file. The name is computed here too, so the common case costs a file test rather
than a Python process.
--]]

local CACHE = 'build/.html-math'
--- Must match `core/html/mathimage.py`'s `VERSION`: it is in the hash, so bumping it there
--- without bumping it here would make the two disagree about a fragment's name.
local VERSION = '1'

--- What marks a fragment as beyond MathJax. chemfig and the `\schemestart` environment it draws
--- reaction arrows in; `\chemname` and `\setchemfig` only ever appear inside one.
local BEYOND = {'chemfig', 'schemestart', 'schemestop', 'chemname', 'setchemfig'}

local language = 'sk'

local function beyond_mathjax(text)
    for _, macro in ipairs(BEYOND) do
        if text:find('\\' .. macro, 1, true) then
            return true
        end
    end
    return false
end

local function exists(path)
    local handle = io.open(path, 'r')
    if handle then
        handle:close()
        return true
    end
    return false
end

--- The cache name, which `mathimage.py` must agree with exactly.
local function digest(text)
    return pandoc.utils.sha1(VERSION .. '\0' .. language .. '\0' .. text):sub(1, 32)
end

local function render(text)
    local svg = CACHE .. '/' .. digest(text) .. '.svg'
    if exists(svg) then
        return svg
    end
    -- a miss: hand it to LaTeX. `pandoc.pipe` raises if the command fails, and the message it
    -- carries is the one `mathimage.py` wrote, which names the LaTeX complaint.
    local produced = pandoc.pipe('python', {'-m', 'core.html.mathimage', language}, text)
    return (produced:gsub('%s+$', ''))
end

return {
    {Meta = function(meta)
        if meta.lang then
            language = pandoc.utils.stringify(meta.lang)
        end
    end},
    {Math = function(element)
        if not beyond_mathjax(element.text) then
            return nil
        end
        local svg = render(element.text)
        -- `chemistry` rather than a caption: the alt text is what a screen reader gets, and a
        -- reaction scheme has no short honest description. The class is for the stylesheet.
        return pandoc.Image({}, svg, '', pandoc.Attr('', {'chemistry'}, {}))
    end},
}
