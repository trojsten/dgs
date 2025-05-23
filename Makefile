# Remove all stupid builtin rules and variables
MAKEFLAGS += --no-builtin-rules --no-builtin-variables --warn-undefined-variables

SUPPORTED_LANGUAGES = sk en cs hu pl es de fr ru fa

path := $(abspath $(lastword $(MAKEFILE_LIST)))
cdir := $(dir $(path))

version   = '4.03'
date      = '2023-09-14'

c_error     := $(shell tput sgr0; tput bold; tput setaf 1)
c_action    := $(shell tput sgr0; tput bold; tput setaf 4)
c_filename  := $(shell tput sgr0; tput setaf 5)
c_extension := $(shell tput sgr0; tput bold; tput setaf 2)
c_special   := $(shell tput sgr0; tput setaf 3)
c_default   := $(shell tput sgr0; tput setaf 7)


# Remove all default suffixes
.SUFFIXES:

.SECONDARY:

# No interactive mode with texfot
# and ignore underfull warnings
TEXFOT_ARGS=--no-interactive \
	--ignore 'Underfull.*'

# On the first run, also ignore missing cross-references and acronyms as they cannot be correct yet
TEXFOT_ARGS_FIRST=${TEXFOT_ARGS} \
	--ignore 'LaTeX Warning: Hyper reference.*' \
	--ignore 'LaTeX Warning: Reference.*' \
	--ignore 'LaTeX Warning: Citation.*'

# xelatex(module, run, texfot_args)
# Compiles a selected target
define xelatex
	@echo -e '$(c_action)[XeLaTeX] Compiling PDF file $(c_filename)$@$(c_action): $(2) run$(c_default)'
	@texfot $(3) xelatex -file-line-error -shell-escape -jobname=$(subst .pdf,,$@) \
		-halt-on-error -synctex=1 -interaction=nonstopmode build/$(1)/$*/$(basename $(notdir $@)).tex
endef

# _pandoc(language, format, pretty_format)
define _pandoc
	@echo -e '$(c_action)[convert] Converting \
		$(c_extension)Markdown$(c_action) file $(c_filename)$<$(c_action) to \
		$(c_extension)$(3)$(c_action) file $(c_filename)$@$(c_action)$(c_default)'
	@mkdir -p $(dir $@)
	python pandoc.py --format $(2) $(1) $< $@ || exit 1;
endef

# lang
# meta file
define _jinja
	@echo -e '$(c_action)[jinja] Rendering \
		$(c_extension)Markdown$(c_action) template $(c_filename)$<$(c_action) to \
		$(c_extension)Markdown$(c_action) file $(c_filename)$@$(c_action)$(c_default)'
	@mkdir -p $(dir $@)
	python jinja.py $(1) $< $@ --context $(2) || exit 1;
endef

# pandoctex(language)
# Converts a file from Markdown to LaTeX
define pandoctex
	$(call _pandoc,$(1),latex,TeX)
endef

# pandochtml(language)
# Converts a file from Markdown to HTML
define pandochtml
	$(call _pandoc,$(1),html,HTML)
endef

# double_xelatex(module)
# Compiles a selected target twice (to ensure references are correct)
define double_xelatex
	mkdir -p $(dir $@)
	$(call xelatex,$(1),primary,${TEXFOT_ARGS_FIRST})
	$(call xelatex,$(1),secondary,${TEXFOT_ARGS})
endef

# copy(extension)
define _copy
	@echo -e '$(c_action)Copying $(c_extension)$(1)$(c_action) file $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@
endef

include modules/*/module.mk

build/core/i18n/%.tex: \
	core/templates/override.jtt
	@mkdir -p $(dir $@)
	python -m core.builder.i18n 'core/i18n/' 'core/templates/' $* -o $(dir $@)

build/core/i18n: \
	$$(foreach lang,$$(SUPPORTED_LANGUAGES),build/core/i18n/$$(lang).tex) ;

# Jinja template rendering md to md
build/%.md: \
	source/%.md \
	$$(abspath source/$$(dir $$*)/meta.yaml)
	$(call _jinja,xx,$(abspath $(dir $<)/meta.yaml))

# DeGeŠ convert Markdown file to TeX (for XeLaTeX)
# THIS IS CURRENTLY HARDCODED TO WORK IN SLOVAK ONLY, OVERRIDE THIS IN MODULE!
build/%.tex: build/%.md
	$(call pandoctex,xx)

# Standalone TeX file from .tikz.tex
build/%.tikz.tex: \
	source/%.tikz \
	core/templates/standalone.jtt
	@mkdir -p $(dir $@)
	./standalone.py $(lang) $< $@

# Copy py files from source to build
build/%.py: source/%.py
	$(call _copy,Python)

# Convert SVG image to PDF (for XeLaTeX output)
build/%.pdf: source/%.svg
	@echo -e '$(c_action)[rsvg-convert] Converting $(c_filename)$<$(c_action) to $(c_extension)PDF$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@ $@-crop
	mv $@-crop $@

build/%.xdv: build/%.tikz.tex
	@echo -e '$(c_action)[xelatex] Rendering $(c_filename)$<$(c_action) to $(c_extension)XDV$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	@texfot xelatex -interaction=nonstopmode -no-pdf -halt-on-error -file-line-error -shell-escape -jobname=$(subst .xdv,,$@) $<

build/%.pdf: build/%.tikz.tex
	@echo -e '$(c_action)[xelatex] Rendering $(c_filename)$<$(c_action) to $(c_extension)PDF$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	@texfot xelatex -interaction=nonstopmode -halt-on-error -file-line-error -shell-escape -jobname=$(subst .pdf,,$@) $<
	@texfot xelatex -interaction=nonstopmode -halt-on-error -file-line-error -shell-escape -jobname=$(subst .pdf,,$@) $<

build/%.svg: build/%.xdv
	@echo -e '$(c_action)[dvisvgm] Rendering $(c_filename)$<$(c_action) to $(c_extension)SVG$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	dvisvgm --no-fonts -o $@ $<

# Render gnuplot file to PDF (for XeLaTeX)
build/%.pdf: build/%.gp
	@echo -e '$(c_action)[gnuplot] Rendering file $(c_filename)$<$(c_action) to $(c_extension)PDF$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cd $(dir $@); gnuplot -e "set terminal pdf font 'TeX Gyre Pagella, 12'; set output '$(notdir $@)'; set fit quiet;" $(notdir $<)

# Copy PDF file (for XeLaTeX)
build/%.pdf: source/%.pdf
	$(call _copy,PDF)

# Copy PNG file (to build)
build/%.png: source/%.png
	$(call _copy,PNG)

# Copy JPG file (to build)
build/%.jpg: source/%.jpg
	$(call _copy,JPG)

# Copy DAT file (to build)
build/%.dat: source/%.dat
	$(call _copy,dat)

# Output PNG from SVG (for web)
output/%.png: source/%.svg
	@echo -e '$(c_action)[rsvg-convert] Converting SVG file $(c_filename)$<$(c_action) to PNG file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	rsvg-convert -f png -h 500 -a -o $@ $<

# Copy SVG (for web)
output/%.svg: source/%.svg
	@echo -e '$(c_action)[rsvg-convert] Converting SVG file $(c_filename)$<$(c_action) to PNG file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	rsvg-convert -f svg -h 500 -a -o $@ $<

# Copy PNG (for web)
output/%.png: source/%.png
	$(call _copy,PNG)

# Copy py (for web)
output/%.py: source/%.py
	$(call _copy,Python)

# Render gnuplot file to PNG (for web)
output/%.png: build/%.gp
	@echo -e '$(c_action)[gnuplot] rendering file $(c_filename)$<$(c_action) to PNG file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cd $(subst output/,build/,$(dir $@)); gnuplot -e "set terminal png font 'TeX Gyre Pagella, 12'; set output '$(notdir $@)'; set fit quiet;" $(notdir $<)
	cp $(subst output/,build/,$@) $@

# Copy JPG (for web)
output/%.jpg: source/%.jpg
	$(call _copy,JPG)

# DeGeŠ convert Markdown to HTML (for web)
output/%.html: source/%.md
	$(call pandochtml,sk)

# DeGeŠ convert Markdown to HTML (for web)
#output/%.html: source/%.md
#	$(call pandochtml,sk)
#	./wr -input $@ -template core/latex/wr.tex --engine xelatex -innerhtml -eqdir .webtex -output $@.conv
#	mv $@.conv $@

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
