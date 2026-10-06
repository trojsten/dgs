.SECONDEXPANSION:

# Every seminar template. The per-document ones are already named by the rule that builds them,
# but `base.jtex` and `base-booklets.jtex` -- which every one of those extends -- were named by no
# rule at all. A wildcard so that a template added later is picked up without anyone remembering
# to list it; regenerating a `.tex` is one fast python call, so the extra breadth costs nothing
# next to shipping a stale document.
SEMINAR_TEMPLATES := $(wildcard modules/seminar/templates/*.jtex)

define RULE_TEMPLATE_SEMINAR
render/seminar/%/$(1).md: \
	source/seminar/$$$$*/$(1).md \
	source/seminar/$$$$*/meta.yaml \
	$$$$(wildcard source/seminar/$$$$*/*.py) \
	$$(PIPELINE_STAMP)
	$$(call jinja,modules.seminar.builder.renderer,$$(lang),source/seminar/$$*/meta.yaml)

build/seminar/%/$(1).tex: \
	render/seminar/$$*/$(1).md \
	build/core/i18n.stamp \
	$$(PIPELINE_STAMP)
	$(call pandoctex,$(lang))
endef
$(foreach target,problem solution,$(eval $(call RULE_TEMPLATE_SEMINAR,$(target))))

# Copy Gnuplot file to build, along with all of its possible .dat prerequisites
render/seminar/%.gp:\
	source/seminar/%.gp \
	$$(subst source/,build/,$$(wildcard $$(dir source/seminar/%.gp)*.dat)) \
	$$(abspath source/seminar/$$(dir $$*)/meta.yaml) \
	$$(PIPELINE_STAMP)
	$(call jinja,modules.seminar.builder.renderer,$(lang),$(abspath $(dir $<)/meta.yaml))

# A picture is a Jinja template, exactly as the gnuplot file above is: the meta beside it is the
# context, so a figure prints the number the meta computes instead of one typed in by hand.
# The meta must be *beside* the picture -- there is no search upwards, and a picture that has no
# meta next to it fails here rather than silently rendering against nothing.
#
# `pathlang` rather than the `$(lang)` the `.gp` rule above passes: seminar is monolingual today,
# so the two agree, but a picture inside a language directory would be rendered in the default
# language by that rule and in its own by this one. The `.gp` rule wants the same treatment and
# does not get it here, because that is a separate defect.
render/seminar/%.tikz:\
	source/seminar/%.tikz \
	$$(abspath source/seminar/$$(dir $$*)/meta.yaml) \
	$$(PIPELINE_STAMP)
	$(call jinja,modules.seminar.builder.renderer,$(call pathlang,$*),$(abspath $(dir $<)/meta.yaml))

render/seminar/%.svg:\
	source/seminar/%.svg \
	$$(abspath source/seminar/$$(dir $$*)/meta.yaml) \
	$$(PIPELINE_STAMP)
	$(call jinja,modules.seminar.builder.renderer,$(call pathlang,$*),$(abspath $(dir $<)/meta.yaml))

### Standalone problems #########################
# One problem, statement and solution, as its own PDF. Everything else here builds at least a
# whole round, which is no use while authoring: it fails for reasons that have nothing to do with
# the problem in front of you.

# % <competition>/<volume>/<semester>/<round>/<problem>
build/seminar/%/build-standalone: \
	$(SEMINAR_TEMPLATES)
	@mkdir -p $(dir $@)
	@echo -e '$(c_action)Building standalone for $(c_filename)$*$(c_action):$(c_default)'
	python -m modules.seminar.builder.standalone $* -o '$(dir $@)'
	touch $@

build/seminar/%/standalone.tex: \
	build/seminar/$$*/build-standalone ;

# Pictures and class files for a single problem.
build/seminar/%/standalone-prerequisites: \
	core/latex/dgs.cls \
	$$(wildcard core/latex/*.tex) \
	$$(subst source/,build/,$$(wildcard source/seminar/$$*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/seminar/$$*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/seminar/$$*/*.pdf)) \
	$$(subst source/,build/,$$(subst .tikz,.pdf,$$(wildcard source/seminar/$$*/*.tikz))) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/seminar/$$*/*.svg))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/seminar/$$*/*.gp))) \
	$$(call truepath, build/seminar/$$*/../../../../copy-static) \
	build/core/i18n.stamp ;

output/seminar/%/standalone.pdf: \
	build/seminar/%/standalone-prerequisites \
	$$(if $$(wildcard source/seminar/$$*/problem.md),build/seminar/$$*/problem.tex) \
	$$(if $$(wildcard source/seminar/$$*/solution.md),build/seminar/$$*/solution.tex) \
	build/seminar/%/standalone.tex
	$(call double_xelatex,seminar)

build/seminar/%/copy-static:
	@mkdir -p $(dir $@).static/
	cp -r source/seminar/$*/.static/ build/seminar/$*/

# Split the path to get the node names
define _prepare_arguments
	@mkdir -p $(dir $@)
	$(eval words := $(subst /, ,$*))
endef

# _prepare_arguments_round(builder)
define prepare_arguments_round
	$(call _prepare_arguments)
	python -m modules.seminar.builder.$(1) 'source/seminar/' 'modules/seminar/templates/' \
		-c $(word 1,$(words)) -v $(word 2,$(words)) -s $(word 3,$(words)) -r $(word 4,$(words)) -o '$(dir $@)' || exit 1;
endef

# Jinja template: render Markdown to Markdown. Here language is currently hardcoded as `sk`.
render/%.md: \
	source/%.md \
	source/$$(dir $$*)/meta.yaml
ifdef lang
	$(call _jinja,$(lang),$(abspath $(dir $<)/meta.yaml))
else
	$(call _jinja,sk,$(abspath $(dir $<)/meta.yaml))
endif

build/seminar/%.tex: \
	render/seminar/%.md \
	build/core/i18n.stamp \
	$$(PIPELINE_STAMP)
	$(call pandoctex,sk)

build/seminar/%/problems.tex build/seminar/%/solutions.tex build/seminar/%/solutions-full.tex build/seminar/%/instagram.tex: \
	modules/seminar/templates/$$(subst .tex,.jtex,$$(notdir $$@)) \
	$$(SEMINAR_TEMPLATES) \
	$$(wildcard source/seminar/$$*/*/meta.yaml) \
	source/seminar/$$*/meta.yaml
	$(call prepare_arguments_round,round)

# competition/volume/semester/round
build/seminar/%/pdf-prerequisites: \
	$$(subst $$(cdir),,$$(abspath build/seminar/$$*/../../../copy-static)) \
	$$(subst source/,build/,$$(wildcard source/seminar/$$*/*/*.pdf)) \
	$$(subst source/,build/,$$(wildcard source/seminar/$$*/*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/seminar/$$*/*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/seminar/$$*/*/*.py)) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/seminar/$$*/*/*.svg))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/seminar/$$*/*/*.gp))) \
	$$(wildcard source/seminar/$$*/*/meta.yaml) \
	source/seminar/$$*/meta.yaml \
	build/core/i18n.stamp ;

output/seminar/%/html-prerequisites: \
	$$(subst source/,output/,$$(wildcard source/seminar/$$*/*/*.jpg)) \
	$$(subst source/,output/,$$(wildcard source/seminar/$$*/*/*.svg)) \
	$$(subst source/,output/,$$(wildcard source/seminar/$$*/*/*.png)) \
	$$(subst source/,output/,$$(wildcard source/seminar/$$*/*/*.py)) \
	$$(subst source/,output/,$$(subst .gp,.png,$$(wildcard source/seminar/$$*/*/*.gp))) \
	$$(subst source/,output/,$$(subst .tikz,.svg,$$(wildcard source/seminar/$$*/*/*.tikz))) ;

output/seminar/%/problems.pdf: \
	modules/seminar/templates/problems.jtex \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/problem.md))) \
	build/seminar/$$*/pdf-prerequisites \
	build/seminar/$$*/problems.tex
	$(call double_xelatex,seminar)

output/seminar/%/solutions.pdf: \
	modules/seminar/templates/solutions.jtex \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/solution.md))) \
	build/seminar/$$*/pdf-prerequisites \
	build/seminar/$$*/solutions.tex
	$(call double_xelatex,seminar)

output/seminar/%/solutions-full.pdf: \
	modules/seminar/templates/solutions-full.jtex \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/problem.md))) \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/solution.md))) \
	build/seminar/$$*/pdf-prerequisites \
	build/seminar/$$*/solutions-full.tex
	$(call double_xelatex,seminar)

output/seminar/%/instagram.pdf: \
	modules/seminar/templates/instagram.jtex \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/problem.md))) \
	build/seminar/$$*/pdf-prerequisites \
	build/seminar/$$*/instagram.tex
	$(call double_xelatex,seminar)

output/seminar/%/instagram: \
	output/seminar/$$*/instagram.pdf
	@echo -e '$(c_action)Splitting $(c_filename)$<$(c_action) to individual images$(c_action):$(c_default)'
	pdftoppm -png -r 150 -aa yes -aaVector yes $< $@

### Batch outputs

output/seminar/%/html-problems: \
	output/seminar/$$*/html-prerequisites \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/seminar/$$*/*/problem.md))) ;

output/seminar/%/html-solutions:\
	output/seminar/$$*/html-prerequisites \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/seminar/$$*/*/solution.md))) ;

output/seminar/%/pdf: \
	output/seminar/$$*/problems.pdf \
	output/seminar/$$*/solutions.pdf ;

output/seminar/%/html: \
	output/seminar/$$*/html-problems \
	output/seminar/$$*/html-solutions ;

output/seminar/%/problems: \
	output/seminar/$$*/problems.pdf \
	output/seminar/$$*/html-problems ;

output/seminar/%/solutions: \
	output/seminar/$$*/solutions.pdf \
	output/seminar/$$*/html-solutions ;

output/seminar/%: \
	output/seminar/$$*/problems \
	output/seminar/$$*/solutions ;
#	output/seminar/$$*/instagram ;

.PHONY:

output/seminar/%/copy: \
	output/seminar/%/
	$(eval words := $(subst /, ,$*))
	python ./dgs-copy.py $(word 1,$(words)) $(word 2,$(words)) $(word 3,$(words)) $(word 4,$(words)) $(user)
