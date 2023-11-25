.SECONDEXPANSION:

build/scholar/%/build-handout: \
	modules/scholar/templates/base.jtt \
	$$(wildcard modules/scholar/templates/handout-*.jtt) \
	source/scholar/$$*/meta.yaml
	@echo -e '$(c_action)Building handout $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/scholar/builder/handout.py 'source/scholar/' 'modules/scholar/templates/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

build/scholar/%/build-homework: \
	modules/scholar/templates/base.jtt \
	$$(wildcard modules/scholar/templates/homework-*.jtt) \
	source/scholar/$$*/meta.yaml
	@echo -e '$(c_action)Building homework $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/scholar/builder/homework.py 'source/scholar/' 'modules/scholar/templates/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

build/scholar/%/build-lecture: \
	modules/scholar/templates/lecture.jtt \
	source/scholar/$$*/meta.yaml
	@echo -e '$(c_action)Building lecture $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/scholar/builder/lecture.py 'source/scholar/' 'modules/scholar/templates/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

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
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*.pdf)) \
	$$(subst source/,build/,$$(wildcard source/scholar/$$*/*/*.pdf)) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/scholar/$$*/*.svg))) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/scholar/$$*/*/*.svg))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/scholar/$$*/*.gp))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/scholar/$$*/*/*.gp))) \
	source/scholar/$$*/meta.yaml ;

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
