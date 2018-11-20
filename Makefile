MAKEFLAGS += --no-builtin-rules
path		:= $(abspath $(lastword $(MAKEFILE_LIST)))
cdir 		:= $(dir $(path))

.SUFFIXES:

.SECONDARY:

version	=			'2.00'
date =				'2018-10-02'

c_error		:= $(shell tput sgr0; tput bold; tput setaf 1)
c_action	:= $(shell tput sgr0; tput bold; tput setaf 4)
c_filename	:= $(shell tput sgr0; tput setaf 5)
c_special	:= $(shell tput sgr0; tput setaf 3)
c_default	:= $(shell tput sgr0; tput setaf 15)

define xelatex
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/$(1)/$*/$(basename $(notdir $@)).tex
endef

# doubletex(module)
define doubletex
    mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): primary run$(c_default)'
	$(call xelatex,$(1))
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): secondary run$(c_default)'
	$(call xelatex,$(1))
endef

include modules.mk
include modules/*/module.mk

# DeGeŠ convert Markdown file to TeX (for XeLaTeX)
input/%.tex: source/%.md
	@echo -e '$(c_action)[Pandoc] Converting Markdown file $(c_filename)$<$(c_action) to TeX file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	python3 core/dgs-convert.py latex $< $@ || exit 1;

# Copy TeX files from source to input
input/%.tex: source/%.tex
	@echo -e '$(c_action)Copying TeX source file $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Convert SVG image to PDF (for XeLaTeX output)
input/%.pdf: source/%.svg
	@echo -e '$(c_action)Converting $(c_filename)$<$(c_action) to PDF file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@ $@-crop
	mv $@-crop $@

# Render gnuplot file to PDF (for XeLaTeX)
input/%.pdf: input/%.gp
	@echo -e '$(c_action)[Gnuplot] Rendering file $(c_filename)$<$(c_action) to PDF file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cd $(dir $@); gnuplot -e "set terminal pdf font 'TeX Gyre Pagella, 12'; set output '$(notdir $@)'; set fit quiet;" $(notdir $<)

# Copy PDF file (for XeLaTeX)
input/%.pdf: source/%.pdf
	@echo -e '$(c_action)Copying PDF file $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Copy PNG file (to input)
input/%.png: source/%.png
	@echo -e '$(c_action)Copying PNG image $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Copy JPG file (to input)
input/%.jpg: source/%.jpg
	@echo -e '$(c_action)Copying JPG image $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Copy DAT file (to input)
input/%.dat: source/%.dat
	@echo -e '$(c_action)Copying data file $(c_filename)$<$(c_action) to file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Output PNG from SVG (for web)
output/%.png: source/%.svg
	@echo -e '$(c_action)Converting SVG file $(c_filename)$<$(c_action) to PNG file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	rsvg-convert -f png -h 300 -a -o $@ $<

# Copy PNG (for web)
output/%.png: source/%.png
	@echo -e '$(c_action)Copying PNG image $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# Render gnuplot file to PNG (for web)
output/%.png: input/%.gp
	@echo -e '$(c_action)[Gnuplot] rendering file $(c_filename)$<$(c_action) to PNG file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cd $(subst output/,input/,$(dir $@)); gnuplot -e "set terminal png font 'TeX Gyre Pagella, 12'; set output '$(notdir $@)'; set fit quiet;" $(notdir $<)
	cp $(subst output/,input/,$@) $@

# Copy JPG (for web)
output/%.jpg: source/%.jpg
	@echo -e '$(c_action)Copying JPG image $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@

# DeGeŠ convert Markdown to web (for web)
output/%.html: source/%.md
	@echo -e '$(c_action)[Pandoc] Converting Markdown file $(c_filename)$<$(c_action) to HTML file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	python3 core/dgs-convert.py html $< $@ || exit 1;


.SECONDEXPANSION:

# Copy Gnuplot file to input, along with all of its possible .dat prerequisites
input/%.gp:\
	source/%.gp\
	$$(subst source/,input/,$$(wildcard $$(dir source/%.gp)*.dat))
	@mkdir -p $(dir $@)
	@echo -e '$(c_action)Copying gnuplot file $(c_filename)$<$(c_action):$(c_default)'
	cp $< $@


output/%/clean:
	rm -rf output/$*/


clean:
	@echo -e '$(c_action)Clean:$(c_default)'
	rm -rf input/

distclean: clean
	@echo -e '$(c_action)Dist clean:$(c_default)'
	rm -rf output/

.PHONY: clean distclean hello
