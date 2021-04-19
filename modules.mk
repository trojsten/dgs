.SECONDEXPANSION:

%/copy-static: \
	$$(wildcard $$(subst input/,source/,$$*)/*)
	@echo -e '$(c_action)Copying static files for $(c_filename)$*$(c_action):$(c_default)'
	@mkdir -p $(dir $@).static/
	cp -r $(subst input/,source/,$*)/.static/ $*/
