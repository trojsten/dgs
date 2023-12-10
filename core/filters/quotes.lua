if FORMAT:match 'latex' then
    function Image (elem)
        return {
            elem,
        }
    end
end

-- if FORMAT:match 'html' then
--     function Image (elem)
--         elem.src = "obrazky/" .. elem.src
--         return elem
--     end
-- end
--
-- if FORMAT:match 'latex' then
--     function Quote (elem)
--         return elem
--     end
-- end