--[[
LaTeX written in prose, which the HTML writer throws away without a word.

siunitx and mhchem both work outside maths, and the sources use that: `\qty{0.900}{\percent}`
and `\ce{NaCl}` are written in running text 550 times across phys and chem, with no dollars
around them. pandoc reads each as a `RawInline` of format `tex` -- correct, and perfectly
handled by the LaTeX writer, which passes it through for siunitx to set.

The HTML writer **drops it silently**. Not a warning, not a placeholder: the sentence
"prikvapkaný jeden ekvivalent \ce{MeLi}." reaches the page as "prikvapkaný jeden ekvivalent ."
and nothing anywhere says a reagent has gone missing. That is the worst shape a defect can
take, and it is why the rule here is inverted: **anything raw becomes maths unless it is known
to be layout**, rather than the other way round. A macro nobody listed then shows up on the
page, possibly wrongly, instead of vanishing.

What is left out is the handful that mean nothing to a browser -- vertical and horizontal
space, a page break, a paragraph. Those are print instructions, and a page that reflows has
nowhere to put them.
--]]

--- Print-only macros: the page has no pages to break and no fixed measure to space against.
local LAYOUT = {
    vspace = true, vspace_ = true, hspace = true, hspace_ = true,
    newpage = true, clearpage = true, pagebreak = true, newline = true,
    noindent = true, par = true, bigskip = true, medskip = true, smallskip = true,
}

--- The control word a fragment opens with, or nil if it does not open with one.
local function head(text)
    return text:match('^%s*\\([a-zA-Z]+)%*?')
end

local function is_layout(text)
    local name = head(text)
    return name ~= nil and LAYOUT[name] == true
end

local function raw_tex(format)
    return format == 'tex' or format == 'latex'
end

return {
    {RawInline = function(element)
        if not raw_tex(element.format) then
            return nil
        end
        if is_layout(element.text) then
            return {}
        end
        return pandoc.Math(pandoc.InlineMath, element.text)
    end},
    {RawBlock = function(element)
        if not raw_tex(element.format) then
            return nil
        end
        if is_layout(element.text) then
            return {}
        end
        return pandoc.Para({pandoc.Math(pandoc.DisplayMath, element.text)})
    end},
}
