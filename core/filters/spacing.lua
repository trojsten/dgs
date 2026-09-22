--[[
    Language-aware non-breaking spaces.

    Slovak and Czech typography forbid a one-letter word at the end of a line, and German
    abbreviations want a thin space between their halves. Authors used to type both by hand --
    `v\ zime`, `d.\thinspace h.` -- which meant the rule lived in their heads and was applied
    to some prepositions and not others, in English where it does not belong, and in exactly
    two of the German solutions.

    The rule belongs to the language being built, so it belongs here. `core/i18n/<lang>.yaml`
    carries the word lists under `typography:` and `core/builder/convertor.py` passes them in
    as metadata; a language that declares nothing gets nothing.

    Why the AST and not a regex over the Markdown: pandoc has already decided what is prose.
    `Math`, `Code`, `RawInline`, `RawBlock`, `CodeBlock`, image and link targets and every
    attribute are separate node types, so a rule written over `Str` and `Space` cannot reach
    them. Nothing has to be re-detected, and nothing can be re-detected wrongly.

    What is emitted is Unicode, not TeX: U+00A0 and U+202F, which pandoc's writers turn into
    `~` and `\,` for LaTeX and into the characters themselves for HTML. One filter, both
    formats, no `FORMAT` branch.
]]

local NBSP = utf8.char(0x00A0)
local THIN = utf8.char(0x202F)

--- Single-letter words that must not end a line, as a set.
local singles = {}
--- `'t. j.'` -> the space that belongs between its halves.
local pairs_glue = {}
--- The same pairs as pandoc's `smart` leaves them -- already glued with U+00A0 -- for the ones
--- that want the narrower space instead. See `Str` below.
local regluing = {}

--- Opening delimiters that may sit in front of a preposition inside the same `Str`.
--- Byte comparison, so multi-byte marks are safe.
local OPENERS = {'(', '[', '{', '"', "'", '„', '“', '«', '‚', '‹'}

local function escape(text)
    return (text:gsub('[%^%$%(%)%%%.%[%]%*%+%-%?]', '%%%0'))
end

local function unopened(text)
    local stripped = true
    while stripped do
        stripped = false
        for _, opener in ipairs(OPENERS) do
            if text:sub(1, #opener) == opener then
                text = text:sub(#opener + 1)
                stripped = true
            end
        end
    end
    return text
end

local function split(text, pattern)
    local out = {}
    for item in tostring(text):gmatch(pattern) do
        table.insert(out, item)
    end
    return out
end

function Meta(meta)
    local function metastring(key)
        return meta[key] and pandoc.utils.stringify(meta[key]) or ''
    end

    for _, word in ipairs(split(metastring('nbsp-singles'), '%S+')) do
        singles[word] = true
    end
    for _, phrase in ipairs(split(metastring('nbsp-pairs'), '[^;]+')) do
        pairs_glue[phrase] = NBSP
    end
    for _, phrase in ipairs(split(metastring('thin-pairs'), '[^;]+')) do
        pairs_glue[phrase] = THIN
        regluing[phrase:gsub(' ', NBSP)] = phrase:gsub(' ', THIN)
    end

    return meta
end

--- `smart` glues some abbreviations on its own, from pandoc's hardcoded English list: it fires
--- for `e.g.`, `i.e.`, `Mr.`, `viz.` and, of all things, `d. h.`, but not for `z. B.`, `t. j.`
--- or `u. a.`. So a German pair may arrive as one `Str` with a full-width non-breaking space in
--- it, which no `Inlines` rule can see. Narrow those.
function Str(element)
    for glued, narrowed in pairs(regluing) do
        element.text = element.text:gsub(escape(glued), narrowed)
    end
    return element
end

--- The space between two inlines is the one node the writers turn into a breakable space, so
--- it is the one node to replace. `SoftBreak` as well as `Space`: with `--wrap=preserve` the
--- source's own line break survives into the TeX, where a newline is an ordinary breakable
--- space, so a preposition at the end of an authored line would still end a typeset line.
---
--- An author who has already written `\ ` leaves no `Space` here at all -- pandoc reads it as
--- U+00A0 inside the `Str` -- so this is idempotent by construction.
function Inlines(inlines)
    for i = #inlines - 1, 2, -1 do
        local gap = inlines[i]
        local before = inlines[i - 1]

        if (gap.t == 'Space' or gap.t == 'SoftBreak') and before.t == 'Str' then
            local after = inlines[i + 1]
            local phrase = (after.t == 'Str') and (before.text .. ' ' .. after.text) or nil

            if phrase and pairs_glue[phrase] then
                inlines[i] = pandoc.Str(pairs_glue[phrase])
            elseif singles[unopened(before.text)] then
                inlines[i] = pandoc.Str(NBSP)
            end
        end
    end

    return inlines
end

--- Two passes: the rule table has to be read before any inline is visited.
return {
    {Meta = Meta},
    {Str = Str, Inlines = Inlines},
}
