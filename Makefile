# Remove all stupid builtin rules and variables
MAKEFLAGS += --no-builtin-rules --no-builtin-variables

SUPPORTED_LANGUAGES = sk en cs hu pl es de fr ru fa uk pt

# Language a picture (`.tikz`, `.gp`) is rendered in. It is not cosmetic: it selects the locale
# the Jinja tags format numbers with, so getting it wrong writes a decimal point where the Slovak
# figure wants a comma.
#
# Resolved per picture, most specific first:
#   1. an explicit `make lang=en ...`, which always wins;
#   2. the language directory the picture sits in, for a picture that belongs to one translation
#      (`problems/johan-august/sk/puzzle.tikz`);
#   3. `$(lang)` below, for the usual case of a picture at the problem level, shared by every
#      translation and with nothing in its path to infer from.
#
# Both rules already referenced `$(lang)`, but nothing ever set it, so they passed an empty
# argument and died on `invalid choice`. That stayed hidden because a stale intermediate in
# `build/` lets make skip the rule -- `make -B` on any `.tikz.tex` shows it.
lang ?= sk
inferred_lang = $(lastword $(filter $(SUPPORTED_LANGUAGES),$(subst /, ,$(dir $(1)))))
pathlang = $(if $(findstring command,$(origin lang)),$(lang),$(or $(call inferred_lang,$(1)),$(lang)))

path := $(abspath $(lastword $(MAKEFILE_LIST)))
cdir := $(dir $(path))

version   = '5.0'
date      = '2025-11-18'

c_error     := $(shell tput sgr0; tput bold; tput setaf 1)
c_action    := $(shell tput sgr0; tput bold; tput setaf 4)
c_filename  := $(shell tput sgr0; tput setaf 5)
c_extension := $(shell tput sgr0; tput bold; tput setaf 2)
c_special   := $(shell tput sgr0; tput setaf 3)
c_default   := $(shell tput sgr0; tput setaf 7)


# Remove all default suffixes
.SUFFIXES:

.SECONDARY:

# Delete a target whose recipe failed. `argparse.FileType('w')` opens the output file when the
# arguments are parsed, so the renderer and the convertor both truncate their target before doing
# any work -- a meta.yaml that fails validation leaves a 0-byte `render/.../solution.md` behind.
# Make then sees a target newer than its prerequisites and skips it, and the *next* build succeeds
# with an empty document: three headings and no text, no error anywhere. A silent empty success is
# far worse than a loud failure, and this is the one-line cure.
.DELETE_ON_ERROR:

# No interactive mode with texfot
# and ignore underfull warnings
TEXFOT_ARGS=--no-interactive \
	--ignore 'Underfull.*'

# On the first run, also ignore missing cross-references and acronyms as they cannot be correct yet
TEXFOT_ARGS_FIRST=${TEXFOT_ARGS} \
	--ignore 'LaTeX Warning: Hyper reference.*' \
	--ignore 'LaTeX Warning: Reference.*' \
	--ignore 'LaTeX Warning: Citation.*'

# Normalise a path containing `..` to one relative to the repository root. Shared: it started in
# modules/naboj/module.mk, but seminar and scholar reach for it too.
define truepath
	$(subst $(cdir),,$(abspath $(1)))
endef

# xelatex(module, run, texfot_args)
# Compiles a selected target
# TeX wraps its log at 79 columns, which chops error messages mid-word -- "File ended while sc /
# anning use of \frac". Widening the line keeps each error readable, and quotable, in one piece.
# Affects only what is printed, never what is typeset.
define xelatex
	@echo -e '$(c_action)[XeLaTeX] Compiling PDF file $(c_filename)$@$(c_action): $(2) run$(c_default)'
	@max_print_line=1000 error_line=254 half_error_line=238 \
		texfot $(3) xelatex -file-line-error -shell-escape -jobname=$(subst .pdf,,$@) \
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

# <builder> <lang> <meta file>
define jinja
	@echo -e '$(c_action)[jinja] Rendering \
		$(c_extension)Markdown template$(c_action) $(c_filename)$<$(c_action) to \
		$(c_extension)Markdown$(c_action) file $(c_filename)$@$(c_action)$(c_default)'
	@mkdir -p $(dir $@)
    python -m $(1) $(2) $< $@ --context $(3) || exit 1;
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
# Just copies a file, also creating the target directory
define _copy
	@echo -e '$(c_action)Copying $(c_extension)$(1)$(c_action) file $(c_filename)$<$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cp $< $@
endef

include modules/*/module.mk

build/core/i18n/%.tex: \
	core/templates/override.jtex
	@mkdir -p $(dir $@)
	python -m core.builder.i18n 'core/i18n/' 'core/templates/' $* -o $(dir $@)

build/core/i18n: \
	$$(foreach lang,$$(SUPPORTED_LANGUAGES),build/core/i18n/$$(lang).tex) ;

# Jinja template: render Markdown to Markdown. XFAIL: this should never be called!
# This rule is here just for debugging -- should be used if no language is provided
# It exits nonzero: the recipe does not produce $@, so reporting success only moves the failure
# to whatever needed the file, which then blames a rule that is not the one at fault. The colour
# was `$(c_err)`, which is not a variable this makefile defines, so the warning came out unpainted.
render/%.md: \
	source/%.md
	@echo -e '$(c_error)Incorrect fall-through rule called on $@!$(c_default)'
	@exit 1

# Pandoc: render Markdown to TeX. XFAIL: this should never be called!
# This rule is here just for debugging -- should be used if no language is provided
build/%.tex: \
	render/%.md
	@echo -e '$(c_error)Incorrect fall-through rule called on $@!$(c_default)'
	@exit 1

# Standalone TeX file from .tikz.tex
build/%.tikz.tex: \
	source/%.tikz \
	core/templates/standalone.jtex
	@mkdir -p $(dir $@)
	./standalone.py $(call pathlang,$*) $< $@

# Copy py files from source to build
# These most probably should not be rendered by Jinja (ToDo verify)
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
	@echo -e '$(c_action)[xelatex] Rendering $(c_filename)$<$(c_action) to ' \
			 '$(c_extension)XDV$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	max_print_line=1000 error_line=254 half_error_line=238 texfot xelatex -interaction=nonstopmode -no-pdf -halt-on-error -file-line-error -shell-escape -jobname=$(subst .xdv,,$@) $<

build/%.pdf: build/%.tikz.tex
	@echo -e '$(c_action)[xelatex] Rendering $(c_filename)$<$(c_action) to' \
			 '$(c_extension)PDF$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	max_print_line=1000 error_line=254 half_error_line=238 texfot xelatex -interaction=nonstopmode -halt-on-error -file-line-error -shell-escape -jobname=$(subst .pdf,,$@) $<
	max_print_line=1000 error_line=254 half_error_line=238 texfot xelatex -interaction=nonstopmode -halt-on-error -file-line-error -shell-escape -jobname=$(subst .pdf,,$@) $<

build/%.svg: build/%.xdv
	@echo -e '$(c_action)[dvisvgm] Rendering $(c_filename)$<$(c_action) to $(c_extension)SVG$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	dvisvgm --no-fonts -o $@ $<

# Render gnuplot file to PDF (for XeLaTeX)
build/%.pdf: build/%.gp
	@echo -e '$(c_action)[gnuplot] Rendering $(c_filename)$<$(c_action) to $(c_extension)PDF$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cd $(dir $@); gnuplot -e "set terminal pdf font 'Minion Pro, 12'; set output '$(notdir $@)'; set fit quiet;" $(notdir $<)

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
	cd $(subst output/,build/,$(dir $@)); gnuplot -e "set terminal pngcairo size 800,600 font 'Minion Pro, 12'; set output '$(notdir $@)'; set fit quiet;" $(notdir $<)
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

build/%.gp:\
	render/%.gp \
	$$(subst source/,build/,$$(wildcard $$(dir source/%.gp)*.dat))
	$(call _copy,gnuplot)

%/copy-static: \
	$$(wildcard $$(subst build/,source/,$$*)/.static/*)
	@echo -e '$(c_action)Copying static files for $(c_filename)$*$(c_action):$(c_default)'
	@mkdir -p $(dir $@).static/
	cp -r $(subst build/,source/,$*)/.static/ $*/
	touch $@


output/%/clean:
	rm -rf output/$*/

output/%/distclean: \
	output/%/clean
	rm -rf build/$*/
	rm -rf render/$*/

clean:
	@echo -e '$(c_action)Clean:$(c_default)'
	rm -rf build/

distclean: clean
	@echo -e '$(c_action)Dist clean:$(c_default)'
	rm -rf output/
	rm -rf render/

.PHONY: clean distclean hello
