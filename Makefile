# Remove all stupid builtin rules and variables
MAKEFLAGS += --no-builtin-rules --no-builtin-variables

SUPPORTED_LANGUAGES = sk en cs hu pl es de fr ru fa uk pt

# Language a picture (`.tikz`, `.svg`, `.gp`) is rendered in. It is not cosmetic: it selects the
# locale the Jinja tags format numbers with, so getting it wrong writes a decimal point where the
# Slovak figure wants a comma.
#
# Resolved per picture, most specific first:
#   1. an explicit `make lang=en ...`, which always wins;
#   2. the language directory the picture sits in, for a picture that belongs to one translation;
#   3. `$(lang)` below, for the usual case of a picture at the problem level, shared by every
#      translation and with nothing in its path to infer from.
#
# Case 2 is kept and currently matches nothing. It used to name `johan-august/sk/puzzle.tikz`,
# which was the only picture in the repository inside a language directory and has been moved up
# beside its meta. Now that a picture is a template it can ask for `(* words.x *)` itself, so a
# per-language copy of a drawing has no reason to exist and the case should stay empty.
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

# The same silent-empty shape from the other direction, and make cannot cure this one: *deleting*
# a source leaves its built `.tex` behind, because a target whose prerequisite has vanished has
# no rule left to remove it. `\protectedInput` then finds that orphan and includes it, so the
# document keeps printing the deleted problem -- or, where the source was empty, keeps printing
# nothing at all where a red `Missing file` box was owed. Deleting the three zero-byte English
# files in `29` moved not one box until the three 1-byte `.tex` files under `build/` went too.
# So: remove a source, remove its counterpart under `build/` and `render/` in the same breath.

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

# Everything whose change can alter a rendered document: the Jinja environment and its filters,
# the quantity classes, the constants table, the i18n words, the per-module renderers, and pandoc's
# wrapper. A render target depends on the *renderer*, not only on its input.
#
# Without this, correcting `QuantityRange.__format__` to round an answer interval outward moved
# five printed intervals and `make` reported every one of them up to date -- `answers.pdf` would
# have been rebuilt from `.tex` files that were already wrong. That is the same class as the `lang`
# bug above: a stale intermediate lets make skip the rule, and the build stays green.
#
# A stamp rather than the list itself. The list is some eighty files and make would compare every
# one of them against each of several thousand render targets; the stamp collapses that to one.
PIPELINE_SOURCES := $(shell find core/builder core/filters core/utilities modules \
                                 \( -name '*.py' -o -name '*.lua' \) \
                                 -not -path '*/__pycache__/*' 2>/dev/null) \
	pandoc.py \
	core/data/constants.yaml \
	$(wildcard core/i18n/*.yaml)

PIPELINE_STAMP := build/.pipeline-stamp

$(PIPELINE_STAMP): $(PIPELINE_SOURCES)
	@mkdir -p $(dir $@)
	@touch $@

include modules/*/module.mk

build/core/i18n/%.tex: \
	core/i18n/%.yaml \
	core/templates/override.jtex
	@mkdir -p $(dir $@)
	python -m core.builder.i18n 'core/i18n/' 'core/templates/' $* -o $(dir $@)

# A stamp *beside* the directory, not the directory itself: a directory's mtime only moves when
# an entry is added or removed, never when one is edited, so `build/core/i18n` was permanently
# older than the `.tex` files inside it and every target depending on it rebuilt every run.
build/core/i18n.stamp: \
	$$(foreach lang,$$(SUPPORTED_LANGUAGES),build/core/i18n/$$(lang).tex)
	@mkdir -p $(@D) && touch $@

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
# From `render/`, not from `source/`: a picture is a Jinja template like everything else, so the
# tags in it are expanded by the per-module `render/<mod>/%.tikz` rule before `standalone.jtex`
# wraps the result. Reading `source/` here is what used to make a tag in a `.tikz` reach LaTeX
# verbatim -- `standalone.jtex` splices the content in as `(* content *)`, and Jinja substitutes a
# variable's value literally rather than rendering it again.
build/%.tikz.tex: \
	render/%.tikz \
	core/templates/standalone.jtex
	@mkdir -p $(dir $@)
	./standalone.py $(call pathlang,$*) $< $@

# Copy py files from source to build
# These most probably should not be rendered by Jinja (ToDo verify)
build/%.py: source/%.py
	$(call _copy,Python)

# Convert SVG image to PDF (for XeLaTeX output)
build/%.pdf: render/%.svg
	@echo -e '$(c_action)[rsvg-convert] Converting $(c_filename)$<$(c_action) to $(c_extension)PDF$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@ $@-crop
	mv $@-crop $@

build/%.pdf: build/%.tikz.tex
	@echo -e '$(c_action)[xelatex] Rendering $(c_filename)$<$(c_action) to' \
			 '$(c_extension)PDF$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	max_print_line=1000 error_line=254 half_error_line=238 texfot xelatex -interaction=nonstopmode -halt-on-error -file-line-error -shell-escape -jobname=$(subst .pdf,,$@) $<
	max_print_line=1000 error_line=254 half_error_line=238 texfot xelatex -interaction=nonstopmode -halt-on-error -file-line-error -shell-escape -jobname=$(subst .pdf,,$@) $<

# A hand-drawn picture, for the web: copied, not round-tripped. It is already an SVG; sending it
# through a PDF and back would cost two conversions to arrive where it started.
#
# Defined before the rule below so that make, which takes the first rule whose prerequisites can
# be made, prefers it. A hand-drawn picture satisfies both (its `render/%.svg` exists, and a
# `build/%.pdf` could be made from it); a TikZ, gnuplot or source-PDF picture satisfies only the
# second. Between them, **`build/%.svg` means "this picture, in the one format the web wants",
# whatever it was drawn in** -- which is what lets a single extension stand for every picture
# downstream.
build/%.svg: render/%.svg
	@echo -e '$(c_action)Copying $(c_extension)SVG$(c_action) file $(c_filename)$<$(c_action):$(c_default)'
	$(call _copy,SVG)

# A gnuplot plot as SVG, drawn by gnuplot rather than converted. See `GNUPLOT_PDF` below for
# why the terminal cannot live in the script.
#
# **A static pattern rule, not an implicit one, and that is the whole reason this works.**
# Make's implicit-rule search takes, in its first pass, any rule whose prerequisites already
# *exist* -- so once the booklet has been built and `build/%.pdf` is sitting there, the
# conversion rule below wins over this one however they are ordered, and the picture you get
# depends on what you happened to build first. A static pattern rule is an explicit rule for
# each of these targets and is not in that search at all.
GNUPLOT_SOURCES := $(shell find source -name '*.gp' 2>/dev/null)
GNUPLOT_SVG_TARGETS := $(patsubst source/%.gp,build/%.svg,$(GNUPLOT_SOURCES))

$(GNUPLOT_SVG_TARGETS): build/%.svg: build/%.gp
	@echo -e '$(c_action)[gnuplot] Rendering $(c_filename)$<$(c_action) to $(c_extension)SVG$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cd $(dir $@); gnuplot -e "$(GNUPLOT_SVG)" \
		-e "set terminal @gpterm size $(GNUPLOT_SVG_SIZE); set output '$(notdir $@)'; set fit quiet;" \
		$(notdir $<)
	@# A script that sets `set terminal pdf` of its own overrides the line above and gnuplot
	@# writes a PDF into a file named `.svg`, with no error anywhere -- `FKS/42/1/1/03` did it
	@# from a `blocks:` entry, which is a `.gp` no grep over `source/**/*.gp` can see. The page
	@# then showed three blank figures. One line is cheaper than finding that again.
	@head -c 5 $@ | grep -q '<' || { \
		echo "$@ is not an SVG: does its script (or a blocks: entry) set its own terminal?" >&2; \
		rm -f $@; exit 1; }

# A picture as SVG, for the web, converted from **the PDF the LaTeX path already built**.
#
# Not from the `.xdv`, which is what the rule here used to do and which never worked: with
# `-no-pdf` the pgf graphics go into the XDV as specials that dvisvgm does not reconstruct, so a
# TikZ drawing came out as its text labels and nothing else -- an 11.8pt sliver of a 333pt
# picture, correct in neither size nor content. The `build/%.xdv` rule that fed it is gone with
# it; between them they had been referenced by nothing since the standalone renderer landed.
#
# Converting the PDF instead costs one indirection and buys the thing worth having: the web
# picture is made from the same artefact as the printed one, so the two cannot drift. It also
# covers every source a `build/%.pdf` can come from -- TikZ, gnuplot, a hand-drawn SVG, a PDF
# copied in -- with one rule rather than four.
#
# **`pdftocairo`, not `dvisvgm --pdf`**, and the difference is not cosmetic. dvisvgm's PDF
# reader is a second implementation of a format poppler already reads, and it gets two things
# wrong that this repository's pictures are made of:
#
#   - **Line widths.** A plot that sets `0.25 w` and `0.5 w` and nothing else came out with its
#     frame and its curve at `stroke-width='4'` -- a heavy black box and a fat line where the
#     booklet has a hairline. (That was `29/chopper`, which is drawn directly now; the defect is
#     not gnuplot's and would bite any PDF that states a width the same way.)
#   - **Embedded rasters.** `29/amusement-speed`'s rollercoaster carries a bitmap of a cart,
#     which dvisvgm shrinks into a smear in the corner.
#
# Both are right in the PDF, right in the booklet, and right out of `pdftocairo`. It converts
# glyphs to `<symbol>` paths of its own accord, so there is still no font to install or serve,
# at the cost of selectable text -- the right trade for a figure and not for the prose round it.
#
# `core/html/texmath.py` still uses dvisvgm, deliberately: it inlines its output into the page,
# where `pdftocairo`'s `<symbol id="glyph0-1">` would collide across a hundred formulas and its
# explicit `fill:rgb(0%,0%,0%)` would defeat the `currentColor` the inlined maths is set in.
# dvisvgm emits bare anonymous paths, which is exactly what that needs, and the maths it is
# given comes from xelatex rather than from cairo.
build/%.svg: build/%.pdf
	@echo -e '$(c_action)[pdftocairo] Rendering $(c_filename)$<$(c_action) to $(c_extension)SVG$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	pdftocairo -svg $< $@

# A gnuplot plot, in each of the two formats, **drawn by gnuplot both times**.
#
# The conversion the rest of the pictures go through -- PDF, then `pdftocairo` -- would work
# here too, and did. Going direct is one step shorter and takes a PDF parser out of the chain,
# which is the part that had been getting it wrong.
#
# What that costs is that the terminal can no longer live in the script, because the two
# terminals disagree about two things and a script cannot state both:
#
#   - **Size.** `pdfcairo` reads a bare number as inches and also takes `cm`; the `svg`
#     terminal takes pixels and rejects `cm` outright. Hence `gppt`, which is one **point** in
#     whatever units this terminal counts in, and a script sizes itself in points.
#   - **Font size.** `pdfcairo` defaults to `fontscale 0.5`, so its `font "Minion Pro, 12"` is
#     6pt on the page; the `svg` terminal has no such halving, and `fontscale` there scales the
#     glyphs **without** scaling the space the layout reserves for them, so it cannot be used to
#     match. `fontscale 1` below removes the hidden factor instead, and the size written is the
#     size set. Proved rather than assumed: the PDFs come out byte-identical either way.
#
# So a script that wants its own canvas writes one line, `set terminal @gpterm size 432*gppt,
# 108*gppt`, and the build says which terminal that is. A script that wants the default writes
# nothing, and the two defaults below are the same picture: `pdfcairo`'s own 5in x 3in, and the
# 360 x 216 points that is.
# `@gpterm` carries the terminal **and its font**, because re-issuing `set terminal` resets
# the font on the `svg` terminal and a script that sizes its own canvas has to re-issue it.
# Two `-e` options rather than one: gnuplot expands a macro while parsing the line it is on,
# so `gpterm` has to be assigned on an earlier line than the `@gpterm` that uses it.
# **The `svg` terminal counts in CSS pixels, 96 to the inch**, where `pdfcairo` counts in
# points, 72. So `gppt` is 4/3 there and 1/72 here, and the font is 8 against 6 -- the same
# type at the same size on the same canvas, said in each terminal's own units. Getting only
# half of that right gives a picture that is the right shape and the wrong size: the web one
# came out a quarter small when the canvas was converted and the font was not.
GNUPLOT_PDF = set macros; gppt = 1.0 / 72; gpterm = 'pdfcairo fontscale 1 font \"Minion Pro, 6\"'
GNUPLOT_SVG = set macros; gppt = 4.0 / 3;  gpterm = 'svg font \"Minion Pro, 8\"'
#: The default canvas: `pdfcairo`'s own 5in x 3in, said twice.
GNUPLOT_PDF_SIZE = 5, 3
GNUPLOT_SVG_SIZE = 480, 288

# Render gnuplot file to PDF (for XeLaTeX)
build/%.pdf: build/%.gp
	@echo -e '$(c_action)[gnuplot] Rendering $(c_filename)$<$(c_action) to $(c_extension)PDF$(c_action) file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	cd $(dir $@); gnuplot -e "$(GNUPLOT_PDF)" \
		-e "set terminal @gpterm size $(GNUPLOT_PDF_SIZE); set output '$(notdir $@)'; set fit quiet;" \
		$(notdir $<)

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
# From `render/` for the same reason the PDF rule is: the web would otherwise ship the tags.
output/%.png: render/%.svg
	@echo -e '$(c_action)[rsvg-convert] Converting SVG file $(c_filename)$<$(c_action) to PNG file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	rsvg-convert -f png -h 500 -a -o $@ $<


# A TikZ picture, for the web: `render/%.tikz` -> `build/%.tikz.tex` -> `build/%.pdf` ->
# `build/%.svg`. Every TikZ drawing in the repository used to be reachable as a PDF and
# unreachable as anything a browser can show.
#
output/%.svg: build/%.svg
	@echo -e '$(c_action)Copying SVG file $(c_filename)$<$(c_action) to $(c_filename)$@$(c_action):$(c_default)'
	$(call _copy,SVG)

# Publish the SVG a `.tikz` renders to (for web)
#
# Nothing new is drawn: the picture has already been through `standalone.jtex` and xelatex to
# become the PDF the booklet sets, and `build/%.svg` only changes that PDF's container.
#
# **Through rsvg-convert, and at the same height as the rule above**, which is the whole reason
# this is not a copy. A `.tikz` keeps the PDF's natural size -- `futile-nine`'s network is 92
# units tall -- while every other picture on the web is published at 500, so a copied one lands
# at a fifth of the size of the drawing beside it. The `<img>` carries `max-height` and no
# height, so the intrinsic size is what the browser uses.
#
# It sits *after* `output/%.svg: render/%.svg` deliberately. Both patterns match the same target
# with the same stem, so make takes the earlier one whose prerequisites it can make: a real
# drawing has a `render/*.svg` and goes through rsvg-convert directly, and only a picture that
# has none -- which is exactly a `.tikz` -- falls through to here. Reversing the two would push
# every SVG in the repository through xelatex.
output/%.svg: build/%.svg
	@echo -e '$(c_action)[rsvg-convert] Converting SVG file $(c_filename)$<$(c_action) to SVG file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	rsvg-convert -f svg -h 500 -a -o $@ $<

# Copy PNG (for web)
output/%.png: source/%.png
	$(call _copy,PNG)

# Copy py (for web)
output/%.py: source/%.py
	$(call _copy,Python)

# A gnuplot plot reaches the web as an SVG, through `build/%.pdf` and `build/%.svg` above --
# the same route a `.tikz` takes. There used to be a second gnuplot run here with
# `-e "set terminal pngcairo"`, and it never worked: every `.gp` opens by setting its own
# `set terminal pdf size W, H`, which runs after the `-e` and wins, so `output/` got a PDF
# carrying a `.png` name and the page showed a broken image.

# Copy JPG (for web)
output/%.jpg: source/%.jpg
	$(call _copy,JPG)

# Markdown to HTML. XFAIL, exactly like the `.tex` fall-through above and for the same reason:
# a module says which language a file is in and where its context lives, and this rule cannot.
#
# It used to read `source/` and hardcode `sk`, which meant the HTML branch skipped the whole Jinja
# stage -- every `(§ … §)` tag reached pandoc verbatim -- and could only ever produce Slovak. The
# per-module rules next to the `.tex` ones are the real ones.
#
# The commented-out `./wr` variant that stood here is gone with it: it drove `--webtex=eqn://`
# through a Go tool that is not in the repository, against `core/latex/wr.tex`, which is not
# either. `core/latex/wrt.tex` is its template, still present and still unused.
output/%.html: \
	render/%.md
	@echo -e '$(c_error)Incorrect fall-through rule called on $@!$(c_default)'
	@exit 1

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

# The targeted version of `clean`, for the one case make cannot handle itself: a problem that has
# been renamed or deleted leaves its `render/` and `build/` copies behind, because a target whose
# prerequisite has vanished has no rule left to remove it (see the note at the head of this file)
# and `.SECONDARY:` keeps every intermediate. `\protectedInput` then goes on including the stale
# `.tex`, so a booklet can print a problem that is no longer in the sources.
#
# `stale` lists and `prune` removes, deliberately two targets: the audit's `build-orphan` reports
# the same thing without a build, and a one-word difference between asking and deleting is not a
# safe thing to offer.
stale:
	@python tools/prune.py

prune:
	@echo -e '$(c_action)Prune:$(c_default)'
	@python tools/prune.py --delete

.PHONY: clean distclean prune stale
