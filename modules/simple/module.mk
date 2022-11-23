.SECONDEXPANSION:

input/simple/%/build-handout: \
	modules/simple/format/format-handout.tex \
	modules/simple/templates/handout-students.tex \
	modules/simple/templates/handout-solutions.tex \
	source/simple/$$*/meta.yaml
	@echo -e '$(c_action)Building handout $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/simple/build/handout.py 'source/simple/' 'modules/simple' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/simple/%/build-homework: \
	modules/simple/format/format-homework.tex \
	modules/simple/templates/homework-students.tex \
	modules/simple/templates/homework-solutions.tex \
	source/simple/$$*/meta.yaml
	@echo -e '$(c_action)Building homework $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/simple/build/homework.py 'source/simple/' 'modules/simple' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/simple/%/build-lecture: \
	modules/simple/format/format-lecture.tex \
	modules/simple/templates/lecture.tex \
	source/simple/$$*/meta.yaml
	@echo -e '$(c_action)Building lecture $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/simple/build/lecture.py 'source/simple/' 'modules/simple' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/simple/%/format-handout.tex: \
	input/simple/$$*/build-handout ;

input/simple/%/format-homework.tex: \
	input/simple/$$*/build-homework ;

input/simple/%/format-lecture.tex: \
	input/simple/$$*/build-lecture ;

input/simple/%/handout-students.tex: \
	input/simple/$$*/build-handout ;

input/simple/%/handout-solutions.tex: \
	input/simple/$$*/build-handout ;

input/simple/%/homework-students.tex: \
	input/simple/$$*/build-homework ;

input/simple/%/homework-solutions.tex: \
	input/simple/$$*/build-homework ;

input/simple/%/lecture.tex: \
	input/simple/$$*/build-lecture ;

input/simple/%/pdf-prerequisites: \
	$$(subst source/,input/,$$(wildcard source/simple/$$*/*.jpg)) \
	$$(subst source/,input/,$$(wildcard source/simple/$$*/*.png)) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/simple/$$*/*.svg))) \
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/simple/$$*/*.gp))) \
	source/simple/$$*/meta.yaml ;

input/simple/%/handout: \
	$$(subst $$(cdir),,$$(abspath input/simple/$$*/../../../copy-static)) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/simple/$$*/*.md))) \
	input/simple/$$*/format-handout.tex \
	input/simple/$$*/pdf-prerequisites ;

input/simple/%/homework: \
	$$(subst $$(cdir),,$$(abspath input/simple/$$*/../../../copy-static)) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/simple/$$*/*.md))) \
	input/simple/$$*/format-homework.tex \
	input/simple/$$*/pdf-prerequisites ;

output/simple/%/handout-students.pdf: \
	input/simple/%/handout \
	input/simple/%/handout-students.tex
	$(call doubletex,simple)

output/simple/%/handout-solutions.pdf: \
	input/simple/%/handout \
	input/simple/%/handout-students.tex \
	input/simple/%/handout-solutions.tex
	$(call doubletex,simple)

output/simple/%/homework-students.pdf: \
	input/simple/%/homework \
	input/simple/%/homework-students.tex
	$(call doubletex,simple)

output/simple/%/homework-solutions.pdf: \
	input/simple/%/homework \
	input/simple/%/homework-students.tex \
	input/simple/%/homework-solutions.tex
	$(call doubletex,simple)

output/simple/%/lecture.pdf: \
	$$(subst $$(cdir),,$$(abspath input/simple/$$*/../copy-static)) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/simple/$$*/*.md))) \
	input/simple/$$*/format-lecture.tex \
	input/simple/$$*/pdf-prerequisites
	$(call doubletex,simple)

.PHONY:
