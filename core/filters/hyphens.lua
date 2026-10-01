--[[
    A hyphen that repeats itself at a line break.

    Czech, Slovak and Portuguese all repeat the hyphen when a hyphenated word breaks at it:
    `anti-inflamatório` sets as `anti-` / `-inflamatório`, never as `anti-` / `inflamatório`.
    Portuguese needs it most often, because enclitic pronouns put a hyphen in ordinary verbs --
    `encontra-se`, `deu-lhe`, `colocou-o` -- but `česko-slovenský` and `bielo-čierny` are the
    same rule.

    The alternative was to forbid the break instead, which is what `\exhyphenpenalty=10000`
    did: correct output, but it throws away a legal breakpoint in languages whose compounds are
    long, and it is not what any of the three norms actually say.

    What is emitted is `\rephyphen`, defined in `core/latex/hacks.tex`. See there for why the
    discretionary is built the way it is; the short version is that babel's `\babelhyphen{repeat}`
    is governed by `\hyphenpenalty` and so cannot be used in a class that switches ordinary
    hyphenation off.

    Why the AST and not a regex over the Markdown, as `spacing.lua` puts it: pandoc has already
    decided what is prose. Hyphens are everywhere in the sources that are *not* prose -- figure
    paths (`northern-sun.svg`), crossref labels (`{#fig:drag-queen}`), siunitx options
    (`forbid-literal-units=false`), code, maths -- and every one of them is a different node type
    that a rule written over `Str` cannot reach. Nothing has to be re-detected, and nothing can be
    re-detected wrongly.

    Unlike `spacing.lua` this one is **LaTeX only**. That filter emits Unicode and serves both
    writers from one rule; there is no Unicode character for a repeating hyphen -- U+00AD SOFT
    HYPHEN inserts a hyphen at the break but does not repeat it -- so HTML keeps the plain hyphen
    and only the LaTeX output carries the rule.
]]

--- Set by `Meta` from `-M repeat-hyphen`, which `core/builder/convertor.py` passes only for a
--- language whose `typography:` asks for it. A language that declares nothing gets nothing.
local enabled = false
--- Spanish only: RAE exempts a hyphen followed by a proper noun, because the capital already
--- shows that the hyphen is not a division mark. `Ruiz-` / `Giménez`, not `Ruiz-` / `-Giménez`.
--- Czech, Slovak, Polish and Portuguese have no such exception -- STN 01 6910 gives
--- `Rakúsko-Uhorsko` and `Bratislava-Ružinov` as cases that *do* repeat.
local not_before_capital = false

--- Lua patterns are byte-oriented, so `%a` does not match `í` or `č`. Every byte of a multi-byte
--- UTF-8 character is >= 0x80 and no ASCII digit or punctuation is, so this is enough: it says
--- "letter" for `a` and for every byte of `í`, and "not a letter" for `2`, `.` and `=`.
local function is_letter(byte)
    return byte:match('%a') ~= nil or byte:byte() >= 128
end

local function truthy(meta, key)
    local flag = meta[key]
    return flag ~= nil and pandoc.utils.stringify(flag) == 'true'
end

function Meta(meta)
    enabled = truthy(meta, 'repeat-hyphen')
    not_before_capital = truthy(meta, 'repeat-hyphen-not-before-capital')
    return meta
end

function Str(elem)
    if not enabled or FORMAT ~= 'latex' then
        return nil
    end
    local text = elem.text
    if not text:find('-', 1, true) then
        return nil
    end

    local out, buf = {}, {}
    for i = 1, #text do
        local c = text:sub(i, i)
        -- Letters both sides, so `2-3`, `-5` and a trailing `anti-` are left alone: the rule is
        -- about a hyphenated *word*, and a range or a dangling hyphen is neither.
        local nxt = text:sub(i + 1, i + 1)
        if c == '-' and i > 1 and i < #text
                and is_letter(text:sub(i - 1, i - 1))
                and is_letter(nxt)
                -- The RAE exception. Only ASCII capitals are tested: a multi-byte letter's
                -- first byte carries no case, and `Ñ-` is not a case anyone writes.
                and not (not_before_capital and nxt:match('%u')) then
            table.insert(out, pandoc.Str(table.concat(buf)))
            -- Braces, or the macro would run into the word that follows it.
            table.insert(out, pandoc.RawInline('latex', '\\rephyphen{}'))
            buf = {}
        else
            table.insert(buf, c)
        end
    end
    if #out == 0 then
        return nil
    end
    table.insert(out, pandoc.Str(table.concat(buf)))
    return out
end

-- Two passes: `Meta` has to have run before any `Str` is looked at, and pandoc does not promise
-- that order within a single filter. `spacing.lua` is built the same way.
return {{Meta = Meta}, {Str = Str}}
