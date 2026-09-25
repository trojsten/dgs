.SECONDEXPANSION:

# Build scripts for language and venue prerequisites

# Shorthand for all i18n YAML definition files
source/naboj/%/i18n: \
	$$(wildcard source/naboj/$$*/.static/i18n/*.yaml) ;

# DeGeŠ convert Markdown file to TeX (for XeLaTeX)
# % <competition>/<volume>/problems/<language>/<problem>
# Overrides global convertor!

# Rules for files that are always translated
# <competition>/<volume>/problems/<problem>/<language>
define NABOJ_TRANSLATABLE
render/naboj/%/$(1).md: \
	$$$$(call truepath, source/naboj/$$$$*/$(1).md) \
	$$$$(call truepath, source/naboj/$$$$*/../meta.yaml) \
	$$(PIPELINE_STAMP)
	$$(eval language := $$(word 5,$$(subst /, ,$$*)))
	$$(call jinja,\
		modules.naboj.builder.renderer,\
		$$(language),\
		$$(abspath $$(dir $$<)/../meta.yaml))

build/naboj/%/$(1).tex: \
	render/naboj/$$$$*/$(1).md \
	build/core/i18n.stamp \
	$$(PIPELINE_STAMP)
	$$(eval language := $$(word 5,$$(subst /, ,$$*)))
	$$(call pandoctex,$$(language))
endef
$(foreach filename,problem solution problem-extra answer-extra,$(eval $(call NABOJ_TRANSLATABLE,$(filename))))

define NABOJ_NONTRANSLATABLE
render/naboj/%/$(1).md: \
	$$$$(call truepath, source/naboj/$$$$*/../$(1).md) \
	$$$$(call truepath, source/naboj/$$$$*/../meta.yaml) \
	$$(PIPELINE_STAMP)
	$$(eval language := $$(word 5,$$(subst /, ,$$*)))
	$$(call jinja,modules.naboj.builder.renderer,$$(language),$$(abspath $$(dir $$<)/meta.yaml))

build/naboj/%/$(1).tex: \
	render/naboj/$$$$*/$(1).md \
	build/core/i18n.stamp \
	$$(PIPELINE_STAMP)
	$$(eval language := $$(word 5,$$(subst /, ,$$*)))
	$$(call pandoctex,$$(language))
endef
$(foreach filename,answer answer-also answer-interval,$(eval $(call NABOJ_NONTRANSLATABLE,$(filename))))

# Copy Gnuplot file to build, along with all of its possible .dat prerequisites
render/naboj/%.gp:\
	source/naboj/%.gp \
	$$(subst source/,build/,$$(wildcard $$(dir source/naboj/%.gp)*.dat)) \
	$$(abspath source/naboj/$$(dir $$*)/meta.yaml) \
	$$(PIPELINE_STAMP)
	$(call jinja,modules.naboj.builder.renderer,$(call pathlang,$*),$(abspath $(dir $<)/meta.yaml))

build/naboj/%.tex: \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$(dir $$*)/../$$(subst .tex,.md,$$(notdir $$@)))) \
	build/core/i18n.stamp \
	$$(PIPELINE_STAMP)
	$(eval language := $(word 5,$(subst /, ,$*)))
	$(call pandoctex,$(language))

# % <competition>/<volume>/languages/<language>

# prepare_arguments(target)
# target = language | venue
define prepare_arguments
	@mkdir -p $(dir $@)
	@echo -e '$(c_action)Building $(1) for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
endef

# The problem *directories*, not the files in them. `booklet.tex` and `answers.tex` fall out of
# this recipe, and which `\protectedInput` lines they carry depends on which files each problem
# has -- `blocks/answer-body.jtex` asks `path_exists` at render time. A file list would not do:
# `wildcard` only names what exists, so deleting `answer-interval.md` would shrink the list and
# leave every remaining prerequisite older than the target. A directory's mtime moves when a file
# inside it is added or removed, which is exactly the event that has to invalidate the booklet.
#
# Without this, deleting `22/solar-shield/answer-interval.md` left the line in `answers.tex` and
# printed `Missing file …/answer-interval.tex` in a red box on the answer sheet, with make green.
#
# Both depths, because the two rule families put files at both. `answer*.md` sits beside the
# unit, so adding or removing one moves `problems/<unit>/`; but `problem.md` and `solution.md`
# live inside `<language>/`, and deleting one of those moves only `problems/<unit>/<language>/`.
# Matching the first depth alone caught the shared files and missed every translated one --
# deleting `29/starlight/en/solution.md` left the booklet believing it was still there.
# The trailing slash is what restricts the glob to directories; `patsubst` takes it back off.
naboj_problem_dirs = $(subst $(cdir),,$(patsubst %/,%,\
	$(wildcard $(abspath source/naboj/$(1)/../../problems)/*/ \
	           $(abspath source/naboj/$(1)/../../problems)/*/*/)))

# Every template the three naboj builders can read, at all three depths `templates/` uses.
#
# A wildcard rather than a list, because the list was wrong in both directions. The four documents
# themselves -- `booklet.jtex`, `answers.jtex`, `solutions.jtex`, `cover.jtex` -- together with
# `blocks/problem.jtex` and `blocks/solution.jtex`, were named by no rule at all, so editing one
# invalidated nothing and `make` reported the old PDF up to date. The blocks that *were* named
# were named on `build/naboj/%/booklet.tex`, whose recipe is empty: make then marks the target out
# of date, runs nothing, and leaves the stale file in place. That is the trap `build-standalone`
# below already documents, and it was documented there while still live here.
#
# So the templates hang off the stamps, which have real recipes, and a template added later is
# picked up without anyone remembering to list it.
NABOJ_TEMPLATES := $(wildcard modules/naboj/templates/*.jtex \
                              modules/naboj/templates/*/*.jtex \
                              modules/naboj/templates/*/*/*.jtex)

build/naboj/%/build-language: \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../../copy-static)) \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../../.static/logo/logo.pdf)) \
	source/naboj/$$*/meta.yaml \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../../meta.yaml)) \
	$$(call naboj_problem_dirs,$$*) \
	$$(NABOJ_TEMPLATES) \
	$$(wildcard source/naboj/$$*/intro.jtex) \
	source/naboj/$$(word 1,$$(subst /, ,$$*))/.static/i18n/$$(word 4,$$(subst /, ,$$*)).yaml
	$(call prepare_arguments,language)
	python -m modules.naboj.builder.language 'source/naboj/' 'modules/naboj/templates/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'
	touch $@

# % <competition>/<volume>/venues/<venue>
# The volume and competition metas were already here and missing from `build-language`, which is
# how `29/meta.yaml` -- the `problems:` running order, the author list, the constants sheet's
# contents -- could change without the booklet moving. The problem directories are here for the
# same reason they are there: `answers-modulo.jtex` embeds an answer block per problem.
build/naboj/%/build-venue: \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/meta.yaml)) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../../meta.yaml)) \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../../copy-static)) \
	$$(call naboj_problem_dirs,$$*) \
	$$(NABOJ_TEMPLATES) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../../i18n))
	$(call prepare_arguments,venue)
	python -m modules.naboj.builder.venue 'source/naboj/' 'modules/naboj/templates/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'
	touch $@

### Input files ###################################################################################

# Language-specific documents: booklet, answer sheet, answer sheet for evaluators, booklet cover
# % <competition>/<volume>/languages/<language>
build/naboj/%/online.tex: \
	modules/naboj/templates/base.jtex \
	modules/naboj/templates/base-booklet.jtex \
	modules/naboj/templates/online.jtex \
    build/naboj/$$*/build-language ;

# % <competition>/<volume>/languages/<language>
build/naboj/%/tearoff.tex: \
	modules/naboj/templates/base.jtex \
	modules/naboj/templates/base-tearoff.jtex \
	modules/naboj/templates/tearoff.jtex \
	modules/naboj/templates/blocks/tearoff/problem.jtex \
	modules/naboj/templates/blocks/tearoff/problem-extra.jtex \
	modules/naboj/templates/blocks/tearoff/bottom.jtex \
	source/naboj/$$(word 1,$$(subst /, ,$$*))/.static/i18n/$$(word 4,$$(subst /, ,$$*)).yaml \
	build/naboj/$$*/build-language ;

# % <competition>/<volume>/languages/<language>
build/naboj/%/booklet.tex build/naboj/%/answers.tex build/naboj/%/cover.tex build/naboj/%/solutions.tex: \
	modules/naboj/templates/base.jtex \
	modules/naboj/templates/base-booklet.jtex \
	modules/naboj/templates/blocks/answer.jtex \
	modules/naboj/templates/blocks/answer-body.jtex \
	modules/naboj/templates/blocks/booklet/footer.jtex \
	modules/naboj/templates/blocks/colophon.jtex \
	build/naboj/$$*/build-language \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) ;

# Introduction page for booklet
# % <competition>/<volume>/languages/<language>
# `intro.jtex` is a prerequisite of the stamp above, not of this target, for the reason the
# stamp's own comment gives: this recipe is empty, so naming the source here marked the target
# out of date, ran nothing, and left the stale `intro.tex` in place. Editing an intro therefore
# changed no PDF at all -- five volumes were printing `problems / pictures / editors / head`,
# the literal keys of the authors mapping, under a heading reading "Zbierku zostavili", and no
# rebuild would have shown it. Every language directory has an intro, but `wildcard` guards the
# stamp against one that does not rather than failing with "No rule to make target".
build/naboj/%/intro.tex: \
	build/naboj/$$*/build-language ;

# Constants sheet
# % <competition>/<volume>/languages/<language>
build/naboj/%/constants.tex: \
	modules/naboj/templates/constants.jtex \
	build/naboj/$$*/build-language ;

# Instructions to be put on the table before the competition (content)
# % <competition>/<volume>/venues/<venue>
build/naboj/%/instructions-inner.tex: \
	$$(wildcard $$(subst $(cdir),,$$(abspath source/naboj/$$*/../../languages/*/instructions-inner.md))) \
	build/naboj/$$*/build-venue ;

# Instructions to be put on the table before the competition (full document)
# % <competition>/<volume>/venues/<venue>
build/naboj/%/instructions.tex: \
	modules/naboj/templates/$$(subst .tex,.jtex,$$(notdir $$@)) \
	build/naboj/$$*/build-venue ;

# % <competition>/<volume>/languages/<language>
build/naboj/%/evaluators.tex: \
	source/naboj/$$*/$$(subst .tex,.jtex,$$(notdir $$@)) \
	build/naboj/$$*/build-language ;

# Instructions before the online competition (content)
build/naboj/%/instructions-online-inner.tex: \
	source/naboj/$$*/_extras/instructions-online-inner.md
	$(eval language := $(word 4,$(subst /, ,$*)))
	@echo -e '$(c_action)[pandoc] Converting Markdown file $(c_filename)$<$(c_action) to TeX file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	python core/pandoc.py --format latex $(language) $< $@ || exit 1;

# Instructions before the online competition (full document)
# % <competition>/<volume>/languages/<language>
build/naboj/%/instructions-online.tex: \
	modules/naboj/templates/$$(notdir $$@) \
	build/naboj/$$*/build-language ;

# PDF prerequisites (pictures, graphs, meta files)
# % <competition>/<volume>
build/naboj/%/pdf-prerequisites: \
	core/latex/dgs.cls \
	$$(wildcard core/latex/*.tex) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*.pdf)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*/*.pdf)) \
	$$(subst source/,build/,$$(subst .tikz,.pdf,$$(wildcard source/naboj/$$*/problems/*/*.tikz))) \
	$$(subst source/,build/,$$(subst .tikz,.pdf,$$(wildcard source/naboj/$$*/problems/*/*/*.tikz))) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/problems/*/*.svg))) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/problems/*/*/*.svg))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/problems/*/*.gp))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/problems/*/*/*.gp))) \
	$$(wildcard source/naboj/$$*/meta.yaml) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../meta.yaml)) \
	build/core/i18n.stamp
	@mkdir -p $(@D) && touch $@

# All problems, solutions and answers for every language, and overall
# <competition>/<volume>
define RULE_TEMPLATE
build/naboj/%/problems/$(1): \
	$$$$(subst source/,build/,$$$$(subst .md,.tex,$$$$(wildcard source/naboj/$$$$*/problems/*/$(1)/problem.md))) \
	$$$$(subst source/,build/,$$$$(subst .md,.tex,$$$$(wildcard source/naboj/$$$$*/problems/*/$(1)/problem-extra.md)))
	@mkdir -p $$(@D) && touch $$@

build/naboj/%/solutions/$(1): \
	$$$$(subst source/,build/,$$$$(subst .md,.tex,$$$$(wildcard source/naboj/$$$$*/problems/*/$(1)/solution.md)))
	@mkdir -p $$(@D) && touch $$@

build/naboj/%/answers/$(1): \
	$$$$(subst answer.md,$(1)/answer.tex,$$$$(subst source/,build/,$$$$(wildcard source/naboj/$$$$*/problems/*/answer.md))) \
	$$$$(subst answer-also.md,$(1)/answer-also.tex,$$$$(subst source/,build/,$$$$(wildcard source/naboj/$$$$*/problems/*/answer-also.md))) \
	$$$$(subst answer-interval.md,$(1)/answer-interval.tex,$$$$(subst source/,build/,$$$$(wildcard source/naboj/$$$$*/problems/*/answer-interval.md))) \
	$$$$(subst source/,build/,$$$$(subst .md,.tex,$$$$(wildcard source/naboj/$$$$*/problems/*/$(1)/answer-extra.md)))
	@mkdir -p $$(@D) && touch $$@

build/naboj/%/$(1): \
	build/naboj/%/problems/$(1) \
	build/naboj/%/solutions/$(1) \
	build/naboj/%/answers/$(1)
	@mkdir -p $$(@D) && touch $$@
endef
$(foreach language,$(SUPPORTED_LANGUAGES),$(eval $(call RULE_TEMPLATE,$(language))))

### Standalone problems #########################
# One problem, one language, one PDF. Everything else in this file builds at least a whole
# volume, which is no use while authoring: it fails for reasons that have nothing to do with
# the problem in front of you. The standalone document deliberately depends on nothing but
# the problem itself, so it still builds when the volume does not.

# % <competition>/<volume>/problems/<problem>/<language>
# The templates are prerequisites of the stamp rather than of `standalone.tex`, because
# `standalone.tex` has an empty recipe -- listing them there would mark it out of date
# without ever regenerating it.
build/naboj/%/build-standalone: \
	$$(NABOJ_TEMPLATES)
	$(call prepare_arguments,standalone)
	python -m modules.naboj.builder.standalone \
		$(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) $(word 5,$(words)) -o '$(dir $@)'
	touch $@

# % <competition>/<volume>/problems/<problem>/<language>
build/naboj/%/standalone.tex: \
	build/naboj/$$*/build-standalone ;

# Pictures, graphs and class files for a single problem: `pdf-prerequisites` narrowed from
# the whole volume down to one problem directory (and its per-language subdirectories).
# % <competition>/<volume>/problems/<problem>
build/naboj/%/standalone-prerequisites: \
	core/latex/dgs.cls \
	$$(wildcard core/latex/*.tex) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/*.pdf)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/*/*.pdf)) \
	$$(subst source/,build/,$$(subst .tikz,.pdf,$$(wildcard source/naboj/$$*/*.tikz))) \
	$$(subst source/,build/,$$(subst .tikz,.pdf,$$(wildcard source/naboj/$$*/*/*.tikz))) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/*.svg))) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/*/*.svg))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/*.gp))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/*/*.gp))) \
	$$(call truepath, build/naboj/$$*/../../../copy-static) \
	build/core/i18n.stamp ;

# % <competition>/<volume>/problems/<problem>/<language>
# Every part is optional -- `$(if $(wildcard ...))` asks the source tree what exists, and the
# document itself guards each `\protectedInput` with `\IfFileExists`, so the two agree.
# Note the `answer*.md` sources live one level up, at the problem, but build into <language>/.
output/naboj/%/standalone.pdf: \
	$$(call truepath, build/naboj/$$*/../standalone-prerequisites) \
	$$(if $$(wildcard source/naboj/$$*/problem.md),build/naboj/$$*/problem.tex) \
	$$(if $$(wildcard source/naboj/$$*/problem-extra.md),build/naboj/$$*/problem-extra.tex) \
	$$(if $$(wildcard source/naboj/$$*/solution.md),build/naboj/$$*/solution.tex) \
	$$(if $$(wildcard source/naboj/$$*/answer-extra.md),build/naboj/$$*/answer-extra.tex) \
	$$(if $$(wildcard source/naboj/$$*/../answer.md),build/naboj/$$*/answer.tex) \
	$$(if $$(wildcard source/naboj/$$*/../answer-also.md),build/naboj/$$*/answer-also.tex) \
	$$(if $$(wildcard source/naboj/$$*/../answer-interval.md),build/naboj/$$*/answer-interval.tex) \
	build/naboj/%/standalone.tex
	$(call double_xelatex,naboj)

### Venues ######################################

# Answers-modulo
# <competition>/<volume>/venues/<venue>
build/naboj/%/answers-modulo.tex: \
	modules/naboj/templates/blocks/answer.jtex \
	modules/naboj/templates/blocks/answer-body.jtex \
	modules/naboj/templates/answers-modulo.jtex \
	build/naboj/$$*/build-venue ;

# All answers
build/naboj/%/answers: \
	$$(addsuffix answer.tex,$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*/))) \
	$$(addsuffix answer-also.tex,$$(subst source/,build/,$$(foreach int,$$(wildcard source/naboj/$$*/problems/*/answer-also.md),$$(wildcard $$(dir $$(int))*/)))) \
	$$(addsuffix answer-interval.tex,$$(subst source/,build/,$$(foreach int,$$(wildcard source/naboj/$$*/problems/*/answer-interval.md),$$(wildcard $$(dir $$(int))*/)))) \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/problems/*/*/answer-extra.md))) ;


### Languages ###################################

# Full booklet
# % <competition>/<volume>/languages/<language>
output/naboj/%/booklet.pdf: \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../$$(word 4,$$(subst /, ,$$*)))) \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../pdf-prerequisites)) \
	$$(subst $$(cdir),,$$(abspath build/naboj/%/../../problems/$$(word 4,$$(subst /, ,$$*)))) \
	$$(subst $$(cdir),,$$(abspath build/naboj/%/../../solutions/$$(word 4,$$(subst /, ,$$*)))) \
	$$(subst $$(cdir),,$$(abspath build/naboj/%/../../answers/$$(word 4,$$(subst /, ,$$*)))) \
	build/naboj/%/intro.tex \
	build/naboj/%/booklet.tex
	$(call double_xelatex,naboj)

# % <competition>/<volume>/languages/<language>
output/naboj/%/solutions.pdf: \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../$$(word 4,$$(subst /, ,$$*)))) \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../pdf-prerequisites)) \
	$$(subst $$(cdir),,$$(abspath build/naboj/%/../../solutions/$$(word 4,$$(subst /, ,$$*)))) \
	build/naboj/%/solutions.tex
	$(call double_xelatex,naboj)

# Full booklet folded for printing
# % <competition>/<volume>/languages/<language>
output/naboj/%/booklet-print.pdf: \
	output/naboj/%/booklet.pdf ;
	pdfbook2 --paper a4paper --outer-margin=30 --inner-margin=50 --top-margin=30 --bottom-margin=30 $<
	mv output/naboj/$*/booklet-book.pdf $@

output/naboj/%/answers.pdf: \
	$$(subst $$(cdir),,$$(abspath build/naboj/%/../../answers/$$(word 4,$$(subst /, ,$$*)))) \
	$$(subst $$(cdir),,$$(abspath build/naboj/%/../../pdf-prerequisites)) \
	build/naboj/%/answers.tex
	$(call double_xelatex,naboj)

# "Virtual tearoffs" for online version, one problem per page
# % <competition>/<volume>/venues/<venue>
output/naboj/%/online.pdf: \
	build/naboj/%/problems \
	build/naboj/%/solutions \
	build/naboj/%/answers \
	build/naboj/%/pdf-prerequisites \
	build/naboj/%/online.tex
	$(call double_xelatex,naboj)
	pdftk $@ burst output $(dir $@)/%02d.pdf

output/naboj/%/constants.pdf: \
	build/naboj/%/constants.tex \
	source/naboj/%/i18n
	$(call double_xelatex,naboj)

output/naboj/%/evaluation.pdf: \
	build/naboj/%/evaluators.tex
	$(call double_xelatex,naboj)

output/naboj/%/instructions-online.pdf: \
	build/naboj/%/pdf-prerequisites \
	build/naboj/%/instructions-online.tex \
	build/naboj/%/instructions-online-inner.tex \
	source/naboj/%/i18n
	$(call double_xelatex,naboj)

output/naboj/%/cover.pdf: \
	build/naboj/%/cover.tex
	$(call double_xelatex,naboj)

output/naboj/%/cover-print.pdf: \
	output/naboj/%/cover.pdf
	pdfjam --quiet --nup "2x1" --landscape --outfile $@ $<

# Tearoffs, three problems per page, aligned for cutting
# <competition>/<volume>/languages/<language>
output/naboj/%/tearoff.pdf: \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../$$(word 4,$$(subst /, ,$$*)))) \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../pdf-prerequisites)) \
	build/naboj/%/tearoff.tex
	$(call double_xelatex,naboj)

# % <competition>/<volume>
output/naboj/%/languages/tearoffs.zip: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/languages/*)),$$(dir)/tearoff.pdf)
	$(foreach path,$^,ln -sf $(notdir $(path)) $(subst tearoff,$(word 6,$(subst /, ,$(path))),$(path));)
	zip --junk-paths $@ $(foreach path,$^,$(subst tearoff,$(word 6,$(subst /, ,$(path))),$(path)))

output/naboj/%/html: \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/naboj/$$*/*/problem.md))) \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/naboj/$$*/*/solution.md))) \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/naboj/$$*/*/answer.md))) ;

# All targets for <language>
# <competition>/<volume>/languages/<language>
output/naboj/%: \
	output/naboj/%/answers.pdf \
	output/naboj/%/constants.pdf \
	output/naboj/%/cover-print.pdf \
	output/naboj/%/booklet.pdf \
	output/naboj/%/tearoff.pdf \
	output/naboj/%/evaluation.pdf \
	output/naboj/%/booklet-print.pdf ;

# <competition>/<volume>
output/naboj/%/booklets: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/languages/*)),$$(dir)/booklet.pdf) ;

# All targets for all languages
# <competition>/<volume>
output/naboj/%/languages: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/languages/*)),$$(dir)) \
	$$@/tearoffs.zip ;

# <competition>/<volume>/venues/<venue>
output/naboj/%/instructions.pdf: \
	build/naboj/%/instructions.tex \
	build/core/i18n.stamp \
	$$(subst source/,build/,$$(wildcard $$(subst $(cdir),,$$(abspath source/naboj/$$*/../../languages/*/instructions-inner.tex)))) \
	build/naboj/$$*/build-venue
	$(call double_xelatex,naboj)

# <competition>/<volume>/venues/<venue>
output/naboj/%/answers-modulo.pdf: \
	$$(subst source/,build/,$$(subst $$(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/*/*.jpg)))) \
	$$(subst source/,build/,$$(subst $$(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/*/*.png)))) \
	$$(subst source/,build/,$$(subst $$(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/*/*.pdf)))) \
	$$(subst source/,build/,$$(subst $$(cdir),,$$(abspath $$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/../../languages/*/*/*.svg))))) \
	$$(subst source/,build/,$$(subst $$(cdir),,$$(abspath $$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/../../languages/*/*/*.gp))))) \
	$$(subst source/,build/,$$(subst .jtex,.tex,$$(subst $$(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/evaluators.jtex))))) \
	$$(subst $$(cdir),,$$(abspath build/naboj/%/../../answers)) \
	$$(subst $$(cdir),,$$(abspath build/naboj/%/../../pdf-prerequisites)) \
	build/naboj/%/answers-modulo.tex \
	build/naboj/$$*/build-venue \
	build/core/i18n.stamp ;
	echo xxx $(subst source/,build/,$(subst $(cdir),,$(abspath $(wildcard source/naboj/$*/../../languages/*/evaluators.jtex))))
	$(call double_xelatex,naboj)


# All targets for <venue>
# <competition>/<volume>/venues/<venue>
output/naboj/%: \
	output/naboj/%/instructions.pdf \
	output/naboj/%/answers-modulo.pdf ;

# All targets for all venues
# <competition>/<volume>
output/naboj/%/venues: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/venues/*)),$$(dir)) ;

# Entire volume
# <competition>/<volume>
output/naboj/%/all: \
	output/naboj/%/languages \
	output/naboj/%/venues ;

output/naboj/%/copy: \
	output/naboj/%
	rsync -rzvhPL output/naboj/$*/ ago:/home/balaz/public_html/naboj/$(subst output/,,$*)
