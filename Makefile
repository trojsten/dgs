MAKEFLAGS += --no-builtin-rules --no-builtin-variables --warn-undefined-variables
path := $(abspath $(lastword $(MAKEFILE_LIST)))
cdir := $(dir $(path))

.SUFFIXES:

.SECONDARY:

version =   '4.01'
date =      '2022-11-25'

c_error		:= $(shell tput sgr0; tput bold; tput setaf 1)
c_action	:= $(shell tput sgr0; tput bold; tput setaf 4)
c_filename	:= $(shell tput sgr0; tput setaf 5)
c_special	:= $(shell tput sgr0; tput setaf 3)
c_default	:= $(shell tput sgr0; tput setaf 15)

# xelatex(module)
# Compiles a selected target
define xelatex
	@texfot xelatex -file-line-error -shell-escape -jobname=$(subst .pdf,,$@) -halt-on-error -synctex=1 -interaction=nonstopmode build/$(1)/$*/$(basename $(notdir $@)).tex
endef

define pandoctex
	@echo -e '$(c_action)[pandoc] Converting Markdown file $(c_filename)$<$(c_action) to TeX file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	python3 core/convert.py latex $(1) $< $@ || exit 1;
endef

define pandochtml
	@echo -e '$(c_action)[pandoc] Converting Markdown file $(c_filename)$<$(c_action) to HTML file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	python3 core/convert.py html $(1) $< $@ || exit 1;
endef

# doubletex(module)
# Compiles a selected target twice (to ensure references are correct)
define doubletex
	mkdir -p $(dir $@)
	@echo -e '$(c_action)[XeLaTeX] Compiling PDF file $(c_filename)$@$(c_action): primary run$(c_default)'
	$(call xelatex,$(1))
	@echo -e '$(c_action)[XeLaTeX] Compiling PDF file $(c_filename)$@$(c_action): secondary run$(c_default)'
	$(call xelatex,$(1))
endef

include modules/*/module.mk

# DeGeŠ convert Markdown file to TeX (for XeLaTeX)
build/%.tex: source/%.md
	$(call pandoctex,sk)

# Copy TeX files from source to build
build/%.tex: source/%.tex
	@echo -e '$(c_action)Copying TeX source file $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Copy py files from source to build
build/%.py: source/%.py
	@echo -e '$(c_action)Copying Python source file $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Convert SVG image to PDF (for XeLaTeX output)
build/%.svg: source/%.svg
	@echo -e '$(c_action)Copying SVG source file $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@
#	@echo -e '$(c_action)[rsvg-convert] Converting $(c_filename)$<$(c_action) to PDF file $(c_filename)$@$(c_action):$(c_default)'
#	@mkdir -p $(dir $@)
#	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
#	pdfcrop $@ $@-crop
#	mv $@-crop $@

# Render gnuplot file to PDF (for XeLaTeX)
build/%.pdf: build/%.gp
	@echo -e '$(c_action)[gnuplot] Rendering file $(c_filename)$<$(c_action) to PDF file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cd $(dir $@); gnuplot -e "set terminal pdf font 'TeX Gyre Pagella, 12'; set output '$(notdir $@)'; set fit quiet;" $(notdir $<)

# Copy PDF file (for XeLaTeX)
build/%.pdf: source/%.pdf
	@echo -e '$(c_action)Copying PDF file $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Copy PNG file (to build)
build/%.png: source/%.png
	@echo -e '$(c_action)Copying PNG image $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Copy JPG file (to build)
build/%.jpg: source/%.jpg
	@echo -e '$(c_action)Copying JPG image $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Copy DAT file (to build)
build/%.dat: source/%.dat
	@echo -e '$(c_action)Copying data file $(c_filename)$<$(c_action) to file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Output PNG from SVG (for web)
output/%.png: source/%.svg
	@echo -e '$(c_action)[rsvg-convert] Converting SVG file $(c_filename)$<$(c_action) to PNG file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	rsvg-convert -f png -h 300 -a -o $@ $<

# Copy SVG (for web)
output/%.svg: source/%.svg
	@echo -e '$(c_action)Copying SVG image $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Copy PNG (for web)
output/%.png: source/%.png
	@echo -e '$(c_action)Copying PNG image $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Copy py (for web)
output/%.py: source/%.py
	@echo -e '$(c_action)Copying Python source file $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Render gnuplot file to PNG (for web)
output/%.png: build/%.gp
	@echo -e '$(c_action)[gnuplot] rendering file $(c_filename)$<$(c_action) to PNG file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cd $(subst output/,build/,$(dir $@)); gnuplot -e "set terminal png font 'TeX Gyre Pagella, 12'; set output '$(notdir $@)'; set fit quiet;" $(notdir $<)
	cp $(subst output/,build/,$@) $@

# Copy JPG (for web)
output/%.jpg: source/%.jpg
	@echo -e '$(c_action)Copying JPG image $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# DeGeŠ convert Markdown to HTML (for web)
output/%.html: source/%.md
	$(call pandochtml,sk)

.SECONDEXPANSION:

# Copy Gnuplot file to build, along with all of its possible .dat prerequisites
build/%.gp:\
	source/%.gp\
	$$(subst source/,build/,$$(wildcard $$(dir source/%.gp)*.dat))
	@mkdir -p $(dir $@)
	@echo -e '$(c_action)Copying gnuplot file $(c_filename)$<$(c_action):$(c_default)'
	cp $< $@

%/copy-static: \
	$$(wildcard $$(subst build/,source/,$$*)/.static/*)
	@echo -e '$(c_action)Copying static files for $(c_filename)$*$(c_action):$(c_default)'
	@mkdir -p $(dir $@).static/
	cp -r $(subst build/,source/,$*)/.static/ $*/


output/%/clean:
	rm -rf output/$*/

output/%/distclean: \
	output/%/clean
	rm -rf build/$*/


clean:
	@echo -e '$(c_action)Clean:$(c_default)'
	rm -rf build/

distclean: clean
	@echo -e '$(c_action)Dist clean:$(c_default)'
	rm -rf output/

.PHONY: clean distclean hello
