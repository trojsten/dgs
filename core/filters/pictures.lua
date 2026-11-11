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
hold `[("height","40mm"),("tearoff_height","30mm")]` -- and then the LaTeX writer drops every key
it does not itself know, emitting `width,height,keepaspectratio` and nothing else. Hence this
filter, which is the only place the value can be caught.

What it emits is `\includegraphics`, not `\insertPicture`: `convertor.py`'s `post_regexes` already
rewrite the one into the other and swap `.svg`/`.gp`/`.tikz` for `.pdf`, passing the option list
through verbatim as `\g<options>`. Emitting the final macro here would mean copying that
extension table into a second place for it to go stale in.
--]]

--- Whether the writer we are feeding sets TeX.
---
--- The HTML writer *would* pass an unknown attribute through, as a stray `tearoff_height="30mm"`
--- on the `<img>`. A web page has no tear-off, so the attribute is dropped there rather than
--- emitted: stripping it is unconditional below and only the raw TeX is guarded.
local function writing_latex()
    return FORMAT:match('latex') ~= nil
end

--- An image carrying a tear-off height, rewritten so the height survives the writer.
---
--- Returns `nil` -- pandoc's "unchanged" -- for every image without one, which is all 2003 of
--- them today. That is what makes this filter additive: a corpus with no `tearoff_height` in it
--- converts byte-identically with the filter in place.
function Image(image)
    local tearoff = image.attributes['tearoff_height']
    if not tearoff then
        return nil
    end
    image.attributes['tearoff_height'] = nil
    if not writing_latex() then
        return image
    end
    -- `width=\linewidth` and `keepaspectratio` are what the LaTeX writer itself adds around a
    -- stated height, and they are what `\insertPicture` is documented against; writing them here
    -- keeps the option list the same shape as every other figure's.
    local height = image.attributes['height']
    local options = {'width=\\linewidth'}
    if height then
        table.insert(options, 'height=' .. height)
    end
    -- After `height`, because keyval honours the last assignment and this one has to win.
    table.insert(options, 'tearoffheight=' .. tearoff)
    table.insert(options, 'keepaspectratio')
    return pandoc.RawInline(
        'tex', '\\includegraphics[' .. table.concat(options, ',') .. ']{' .. image.src .. '}')
end
