.SECONDEXPANSION:

define RULE_TEMPLATE_SCHOLAR
render/scholar/%/$(1).md: \
	source/scholar/$$$$*/$(1).md \
	source/scholar/$$$$*/meta.yaml \
	$$(PIPELINE_STAMP)
	$$(call jinja,modules.scholar.builder.renderer,$$(lang),source/scholar/$$*/meta.yaml)

build/scholar/%/$(1).tex: \
	render/scholar/$$*/$(1).md \
	build/core/i18n.stamp \
	$$(PIPELINE_STAMP)
	$(call pandoctex,$(lang))
endef
$(foreach target,text problem solution,$(eval $(call RULE_TEMPLATE_SCHOLAR,$(target))))

# Copy Gnuplot file to build, along with all of its possible .dat prerequisites
render/scholar/%.gp:\
	source/scholar/%.gp \
	$$(subst source/,build/,$$(wildcard $$(dir source/scholar/%.gp)*.dat)) \
	$$(abspath source/scholar/$$(dir $$*)/meta.yaml) \
	$$(PIPELINE_STAMP)
	$(call jinja,modules.scholar.builder.renderer,$(lang),$(abspath $(dir $<)/meta.yaml))

# A picture is a Jinja template, exactly as the gnuplot file above is: the meta beside it is the
# context, so a figure prints the number the meta computes instead of one typed in by hand.
# The meta must be *beside* the picture -- there is no search upwards, and a picture that has no
# meta next to it fails here rather than silently rendering against nothing. Nothing builds
# `scholar` today; when something does, `TA1/2022/handouts/07/1-lines/fraunhofer.svg` is the one
# picture whose meta is a directory up and it wants moving beside it.
#
# `pathlang` rather than the `$(lang)` the `.gp` rule above passes; that rule wants the same
# treatment and does not get it here, because it is a separate defect.
render/scholar/%.tikz:\
	source/scholar/%.tikz \
	$$(abspath source/scholar/$$(dir $$*)/meta.yaml) \
	$$(PIPELINE_STAMP)
	$(call jinja,modules.scholar.builder.renderer,$(call pathlang,$*),$(abspath $(dir $<)/meta.yaml))

render/scholar/%.svg:\
	source/scholar/%.svg \
	$$(abspath source/scholar/$$(dir $$*)/meta.yaml) \
	$$(PIPELINE_STAMP)
	$(call jinja,modules.scholar.builder.renderer,$(call pathlang,$*),$(abspath $(dir $<)/meta.yaml))

### Standalone units ############################
# One unit -- a sheet's text, or one problem with its solution -- as its own PDF. Everything else
# here builds a whole handout, which is no use while authoring.

# % <course>/<year>/<kind>/<issue>[/<problem>]
build/scholar/%/build-standalone: \
	modules/scholar/templates/base.jtex \
	modules/scholar/templates/standalone.jtex
	@mkdir -p $(dir $@)
	@echo -e '$(c_action)Building standalone for $(c_filename)$*$(c_action):$(c_default)'
	python -m modules.scholar.builder.standalone $* -o '$(dir $@)'
	touch $@

build/scholar/%/standalone.tex: \
	build/scholar/$$*/build-standalone ;

build/scholar/%/standalone-prerequisites: \
	core/latex/dgs.cls \
	$$(wildcard core/latex/*.tex) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*.pdf)) \
	$$(subst source/,build/,$$(subst .tikz,.pdf,$$(wildcard source/scholar/$$*/*.tikz))) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/scholar/$$*/*.svg))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/scholar/$$*/*.gp))) \
	build/core/i18n.stamp ;

# `text` belongs to a sheet and `problem`/`solution` to a problem inside one; the wildcards pick
# whichever of the three actually exist, so one rule serves both depths.
output/scholar/%/standalone.pdf: \
	build/scholar/%/standalone-prerequisites \
	$$(subst $$(cdir),,$$(abspath build/scholar/$$(word 1,$$(subst /, ,$$*))/copy-static)) \
	$$(if $$(wildcard source/scholar/$$*/text.md),build/scholar/$$*/text.tex) \
	$$(if $$(wildcard source/scholar/$$*/problem.md),build/scholar/$$*/problem.tex) \
	$$(if $$(wildcard source/scholar/$$*/solution.md),build/scholar/$$*/solution.tex) \
	build/scholar/%/standalone.tex
	$(call double_xelatex,scholar)

build/scholar/%/build-handout: \
	modules/scholar/templates/base.jtex \
	$$(wildcard modules/scholar/templates/handout-*.jtex) \
	source/scholar/$$*/meta.yaml
	@echo -e '$(c_action)Building handout $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python -m modules.scholar.builder.handout 'source/scholar/' 'modules/scholar/templates/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

build/scholar/%/build-homework: \
	modules/scholar/templates/base.jtex \
	$$(wildcard modules/scholar/templates/homework-*.jtex) \
	source/scholar/$$*/meta.yaml
	@echo -e '$(c_action)Building homework $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python -m modules.scholar.builder.homework 'source/scholar/' 'modules/scholar/templates/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

build/scholar/%/problem.tex: \
	render/scholar/$$*/problem.md \
	build/core/i18n.stamp \
	$$(PIPELINE_STAMP)
	$(call pandoctex,$(lang))

build/scholar/%/solution.tex: \
	render/scholar/$$*/solution.md \
	build/core/i18n.stamp \
	$$(PIPELINE_STAMP)
	$(call pandoctex,$(lang))

build/scholar/%/text.tex: \
	render/scholar/$$*/text.md \
	build/core/i18n.stamp \
	$$(PIPELINE_STAMP)
	$(call pandoctex,$(lang))

# <subject>/<year>/<target>/<issue>
build/scholar/%/handout-students.tex: \
	build/scholar/$$*/build-handout ;

build/scholar/%/handout-solutions.tex: \
	build/scholar/$$*/build-handout ;

build/scholar/%/handout-solved.tex: \
	build/scholar/$$*/build-handout ;

build/scholar/%/homework-students.tex: \
	build/scholar/$$*/build-homework ;

build/scholar/%/homework-solutions.tex: \
	build/scholar/$$*/build-homework ;

# <subject>/<year>/<target>/<issue>
build/scholar/%/pdf-prerequisites: \
	$$(subst $$(cdir),,$$(abspath build/scholar/$$(word 1,$$(subst /, ,$$*))/copy-static)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*/*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*/*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*.pdf)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*/*.pdf)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*/*/*.pdf)) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/scholar/$$*/*.svg))) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/scholar/$$*/*/*.svg))) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/scholar/$$*/*/*/*.svg))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/scholar/$$*/*.gp))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/scholar/$$*/*/*.gp))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/scholar/$$*/*/*/*.gp))) \
	source/scholar/$$*/meta.yaml \
	build/core/i18n.stamp ;

build/scholar/%/handout: \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*.md))) \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*/*.md))) \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*/*/*.md))) \
	build/scholar/$$*/pdf-prerequisites ;

build/scholar/%/homework: \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*.md))) \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*/*.md))) \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*/*/*.md))) \
	build/scholar/$$*/pdf-prerequisites ;

output/scholar/%/handout-students.pdf: \
	build/scholar/%/handout \
	build/scholar/%/handout-students.tex
	$(call double_xelatex,scholar)

output/scholar/%/handout-solutions.pdf: \
	build/scholar/%/handout \
	build/scholar/%/handout-solutions.tex
	$(call double_xelatex,scholar)

output/scholar/%/handout-solved.pdf: \
	build/scholar/%/handout \
	build/scholar/%/handout-solved.tex
	$(call double_xelatex,scholar)

output/scholar/%/handouts: \
	$$(subst meta.yaml,handout-students.pdf,$$(subst source,output,$$(wildcard source/scholar/$$*/handouts/*/meta.yaml))) \
	$$(subst meta.yaml,handout-solved.pdf,$$(subst source,output,$$(wildcard source/scholar/$$*/handouts/*/meta.yaml))) ;

output/scholar/%/homework-students.pdf: \
	build/scholar/%/homework \
	build/scholar/%/homework-students.tex
	$(call double_xelatex,scholar)

output/scholar/%/homework-solutions.pdf: \
	build/scholar/%/homework \
	build/scholar/%/homework-solutions.tex
	$(call double_xelatex,scholar)

output/scholar/%/homework: \
	$$(subst meta.yaml,homework-students.pdf,$$(subst source,output,$$(wildcard source/scholar/$$*/homework/*/meta.yaml))) \
	$$(subst meta.yaml,homework-solutions.pdf,$$(subst source,output,$$(wildcard source/scholar/$$*/homework/*/meta.yaml))) ;

.PHONY:
