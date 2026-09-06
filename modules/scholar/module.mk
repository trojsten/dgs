.SECONDEXPANSION:

define RULE_TEMPLATE_SCHOLAR
render/scholar/%/$(1).md: \
	source/scholar/$$$$*/$(1).md \
	source/scholar/$$$$*/meta.yaml \
	$$(PIPELINE_STAMP)
	$$(call jinja,modules.scholar.builder.renderer,$$(lang),source/scholar/$$*/meta.yaml)

build/scholar/%/$(1).tex: \
	render/scholar/$$*/$(1).md \
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

### Standalone units ############################
# One unit -- a sheet's text, or one problem with its solution -- as its own PDF. Everything else
# here builds a whole handout, which is no use while authoring.

# % <course>/<year>/<kind>/<issue>[/<problem>]
build/scholar/%/build-standalone: \
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
	build/core/i18n ;

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

build/scholar/%/build-lecture: \
	modules/scholar/templates/lecture.jtex \
	source/scholar/$$*/meta.yaml
	@echo -e '$(c_action)Building lecture $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python -m modules.scholar.builder.lecture 'source/scholar/' 'modules/scholar/templates/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

build/scholar/%/problem.tex: \
	render/scholar/$$*/problem.md \
	$$(PIPELINE_STAMP)
	$(call pandoctex,$(lang))

build/scholar/%/solution.tex: \
	render/scholar/$$*/solution.md \
	$$(PIPELINE_STAMP)
	$(call pandoctex,$(lang))

build/scholar/%/text.tex: \
	render/scholar/$$*/text.md \
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

build/scholar/%/lecture.tex: \
	build/scholar/$$*/build-lecture ;

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
	build/core/i18n ;

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

output/scholar/%/lecture.pdf: \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*.md))) \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*/*.md))) \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*/*/*.md))) \
	build/scholar/$$*/lecture.tex \
	build/scholar/$$*/pdf-prerequisites
	$(call double_xelatex,scholar)

.PHONY:
