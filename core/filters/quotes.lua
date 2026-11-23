--[[
    Quotation marks, in the language being built.

    **LaTeX does not need this and HTML does.** `markdown+smart` turns `"…"` into a `Quoted`
    node and each writer then renders it: the LaTeX writer emits `\enquote{…}`, which csquotes
    sets per language from the `\setquotestyle` in `build/core/i18n/<lang>.tex`, so the booklet
    has been right all along. The HTML writer has no such mechanism and emits **pandoc's own**
    marks, which are English: `“dačo”` where Slovak sets `„dačo“`, on every page of every
    language but English.

    It had been noticed. `core/tests/test_convertor.py`'s `TestQuotes` asserted `„dačo“` for
    both formats and was skipped on 2023-12-11 with the reason *"We have switched to \enquote
    for LaTeX, HTML port underway"*. The LaTeX half of that is done; this is the port.

    `core/i18n/<lang>.yaml` already carries the pair under `quotes:` -- it has to, because
    `override.jtex` reads the same keys to configure csquotes -- so there is one statement of
    what a language's quotes are and both formats now read it. French is the one that shows why
    the strings are taken as written rather than assembled: its marks carry their own spacing,
    `« ` and ` »`.

    Only `html` is rewritten. Touching the LaTeX path would replace `\enquote{}` with literal
    characters and take csquotes' nesting -- a quote inside a quote becomes the inner pair --
    away with it.
]]

local open, close = '', ''
local single_open, single_close = '', ''

function Meta(meta)
    local function metastring(key)
        return meta[key] and pandoc.utils.stringify(meta[key]) or ''
    end
    open, close = metastring('quote-open'), metastring('quote-close')
    single_open, single_close = metastring('quote-single-open'), metastring('quote-single-close')
end

--- One `Quoted` node, flattened into its content between two literal marks.
local function quoted(elem)
    if open == '' then                     -- a language that declares none keeps pandoc's
        return nil
    end
    local marks = elem.quotetype == 'SingleQuote'
        and {single_open ~= '' and single_open or open,
             single_close ~= '' and single_close or close}
        or {open, close}
    local out = pandoc.List({pandoc.Str(marks[1])})
    out:extend(elem.content)
    out:insert(pandoc.Str(marks[2]))
    return out
end

if FORMAT:match 'html' then
    return {
        {Meta = Meta},
        {Quoted = quoted},
    }
end

-- The LaTeX writer already does the right thing through csquotes; this one line is what it has
-- always needed from here. An `Image` reaching the writer unchanged keeps the attribute block
-- `core/filters/pictures.lua` depends on.
if FORMAT:match 'latex' then
    function Image(elem)
        return {
            elem,
        }
    end
end
