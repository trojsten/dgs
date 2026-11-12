--[[
A figure's height in the tear-off, where it differs from its height everywhere else.

A problem's `.tex` is built **once** and every document inputs that same file -- the booklet and
`problems.pdf` through `blocks/problem.jtex`, the tear-off through `blocks/tearoff/problem.jtex`,
character-for-character the same `\protectedInput` path. So the renderer cannot know which
document will set what it writes, and `(§ pictures.x(height='55mm') §)` changes every one of them
at once. That is per *language*, which is a different question from per *document*, and the
tear-off is the document that needs the second one: each problem sits in a fixed-height minipage
of 94mm (phys) or 143mm (chem), while a booklet column is free-flowing.

So the value is carried into the TeX and chosen there. `tearoffheight` is an ordinary `Gin` key,
ignored by default and redefined by `\tearoffPictures` inside the tear-off's minipage -- the same
shape as `\tightPictures`, where the *including* context decides and the fragment is untouched.

**pandoc will not carry it for us.** The attribute survives into the AST -- an `Image` really does
hold `[("height","40mm"),("th","30mm")]` -- and then the LaTeX writer drops every key it does
not itself know, emitting `width,height,keepaspectratio` and nothing else. Hence this
filter, which is the only place the value can be caught.

What it emits is `\includegraphics`, not `\insertPicture`: `convertor.py`'s `post_regexes` already
rewrite the one into the other and swap `.svg`/`.gp`/`.tikz` for `.pdf`, passing the option list
through verbatim as `\g<options>`. Emitting the final macro here would mean copying that
extension table into a second place for it to go stale in.

**Rebuilding the option list means owning everything pandoc's writer did with it**, and that is
the whole of the risk here. Two things follow, and neither is optional:

- a dimension is *translated*, not copied. `height=50%` is pandoc's notation for half the text
  height and its writer emits `0.5\textheight`; copied verbatim, the `%` is TeX's comment
  character and swallows the rest of the option list, the closing bracket and the file name with
  it, so the figure fails somewhere else entirely with nothing pointing back here;
- every other attribute is **passed through**, because an author who wrote one meant it. pandoc's
  own writer keeps `page`, `trim`, `clip` and `alt` and silently discards the rest of graphicx's
  keys -- `angle`, `scale`, `origin`, `draft`, `viewport` -- and a filter that reproduced that
  whitelist would be a second copy of pandoc's taste, going stale on pandoc's own schedule.
  Here an unknown key reaches graphicx, which either honours it or stops the build naming it.
  That is the loud half of the same bargain.

`tp`, the tear-off pregap, rides along the same way and for the same reason, except that it is
not a graphicx key at all: a vertical skip has to be laid down *before* the drawing, so the filter
writes `\tearoffPregap{…}` ahead of the include. That macro is a no-op everywhere but the
tear-off, so a gap tuned for a 94mm box cannot leak into a booklet column.

Only a figure that declares one of the two goes through any of this. Every other image returns
pandoc's *unchanged*, which is what keeps a corpus with none in it -- all 2003 of today's figures
-- byte-identical with the filter in place.
--]]

--- Whether the writer we are feeding sets TeX.
---
--- The HTML writer *would* pass an unknown attribute through, as a stray `th="30mm"` on the
--- `<img>`. A web page has no tear-off, so the attribute is dropped there rather than
--- emitted: stripping it is unconditional below and only the raw TeX is guarded.
local function writing_latex()
    return FORMAT:match('latex') ~= nil
end

--- The two attributes this filter spells itself; everything else is passed through as written.
local OWN = {width = true, height = true}

--- A pandoc dimension in the spelling graphicx reads.
---
--- `%` is pandoc's, not graphicx's: a percentage is a fraction of `\linewidth` for a width and of
--- `\textheight` for a height, and pandoc's writer resolves it before the value ever reaches TeX.
--- `%.14g` is what reproduces that spelling -- `60%` is `0.6`, `100%` is `1`, `33.5%` is `0.335`,
--- none of them with a trailing zero pandoc does not write. A sign is allowed because
--- the pregap `tp` goes through here too, and a gap is usually negative.
local function dimension(value, relative)
    local percent = value:match('^%s*(%-?[%d%.]+)%s*%%%s*$')
    if percent then
        return string.format('%.14g', tonumber(percent) / 100) .. relative
    end
    return value
end

--- An image carrying a tear-off height, rewritten so the height survives the writer.
---
--- Returns `nil` -- pandoc's "unchanged" -- for every image without one, which is all 2003 of
--- them today. That is what makes this filter additive: a corpus with no `th` in it converts
--- byte-identically with the filter in place.
function Image(image)
    local tearoff = image.attributes['th']
    local pregap = image.attributes['tp']
    if not tearoff and not pregap then
        return nil
    end
    image.attributes['th'] = nil
    image.attributes['tp'] = nil
    if not writing_latex() then
        return image
    end
    local width = image.attributes['width']
    local height = image.attributes['height']
    if not width and not height then
        -- A figure with neither dimension is an authoring error, and it already has an owner:
        -- pandoc wraps an unsized image in `\pandocbounded`, which `convertor.py` refuses by
        -- name. Handing it back unchanged keeps that one message rather than inventing a second
        -- -- the build fails either way, so the tear-off's own keys are lost to a failed
        -- build and not to a page.
        return image
    end
    -- `width=\linewidth` and `height=\textheight` are what the LaTeX writer itself supplies for
    -- whichever dimension is missing, with `keepaspectratio` to make the stated one the real
    -- constraint; with both stated it supplies neither, because the author has given a box.
    local options = {
        'width=' .. (width and dimension(width, '\\linewidth') or '\\linewidth'),
        'height=' .. (height and dimension(height, '\\textheight') or '\\textheight'),
    }
    if tearoff then
        -- After `height`, because keyval honours the last assignment and this one has to win.
        table.insert(options, 'tearoffheight=' .. dimension(tearoff, '\\textheight'))
    end
    if not (width and height) then
        table.insert(options, 'keepaspectratio')
    end
    -- Braced, because a value holding a comma -- `trim` takes four lengths and pandoc writes them
    -- bare -- would otherwise split into options of its own. keyval strips one level, so this is
    -- the same value to every key that already worked. Last, so that an author restating one of
    -- ours, `keepaspectratio=false` on a figure that must be squashed, wins by position.
    for _, attribute in ipairs(image.attributes) do
        if not OWN[attribute[1]] then
            table.insert(options, attribute[1] .. '={' .. attribute[2] .. '}')
        end
    end
    -- Before the include, because the skip belongs above the drawing and `\insertPicture` --
    -- which `convertor.py` rewrites this into -- opens a `center` of its own.
    local prefix = ''
    if pregap then
        prefix = '\\tearoffPregap{' .. dimension(pregap, '\\textheight') .. '}'
    end
    return pandoc.RawInline(
        'tex',
        prefix .. '\\includegraphics[' .. table.concat(options, ',') .. ']{' .. image.src .. '}')
end
