%/copy-static:
	@mkdir -p $(dir $@)static/
	cp -r $(subst input/,source/,$*)/static/ $*/

