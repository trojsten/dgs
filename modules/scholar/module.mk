.SECONDEXPANSION:

input/scholar/%/build-handout: \
	modules/scholar/format/format-handout.tex \
	modules/scholar/templates/handout-students.tex \
	modules/scholar/templates/handout-solutions.tex \
	source/scholar/$$*/meta.yaml
	@echo -e '$(c_action)Building handout $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/scholar/build/handout.py 'source/scholar/' 'modules/scholar' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/scholar/%/build-homework: \
	modules/scholar/format/format-homework.tex \
	modules/scholar/templates/homework.tex \
	source/scholar/$$*/meta.yaml
	@echo -e '$(c_action)Building homework $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/scholar/build/homework.py 'source/scholar/' 'modules/scholar' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/scholar/%/build-lecture: \
	modules/scholar/format/format-lecture.tex \
	modules/scholar/templates/lecture.tex \
	source/scholar/$$*/meta.yaml
	@echo -e '$(c_action)Building lecture $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/scholar/build/lecture.py 'source/scholar/' 'modules/scholar' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/scholar/%/format-handout.tex: \
	input/scholar/$$*/build-handout ;

input/scholar/%/format-homework.tex: \
	input/scholar/$$*/build-homework ;

input/scholar/%/format-lecture.tex: \
	input/scholar/$$*/build-lecture ;

input/scholar/%/handout-students.tex: \
	input/scholar/$$*/build-handout ;

input/scholar/%/handout-solutions.tex: \
	input/scholar/$$*/build-handout ;

input/scholar/%/homework.tex: \
	input/scholar/$$*/build-homework ;

input/scholar/%/lecture.tex: \
	input/scholar/$$*/build-lecture ;

input/scholar/%/pdf-prerequisites: \
	$$(subst source/,input/,$$(wildcard source/scholar/$$*/*.jpg)) \
	$$(subst source/,input/,$$(wildcard source/scholar/$$*/*.png)) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/scholar/$$*/*.svg))) \
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/scholar/$$*/*.gp))) \
	source/scholar/$$*/meta.yaml ;

input/scholar/%/handout: \
	$$(subst $$(cdir),,$$(abspath input/scholar/$$*/../../../copy-static)) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*.md))) \
	input/scholar/$$*/format-handout.tex \
	input/scholar/$$*/pdf-prerequisites ;

output/scholar/%/handout-students.pdf: \
	input/scholar/%/handout \
	input/scholar/%/handout-students.tex
	$(call doubletex,scholar)

output/scholar/%/handout-solutions.pdf: \
	input/scholar/%/handout \
	input/scholar/%/handout-students.tex \
	input/scholar/%/handout-solutions.tex
	$(call doubletex,scholar)

output/scholar/%/homework.pdf: \
	$$(subst $$(cdir),,$$(abspath input/scholar/$$*/../../../copy-static)) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*.md))) \
	input/scholar/$$*/homework.tex \
	input/scholar/$$*/format-homework.tex \
	input/scholar/$$*/pdf-prerequisites
	$(call doubletex,scholar)

output/scholar/%/lecture.pdf: \
	$$(subst $$(cdir),,$$(abspath input/scholar/$$*/../copy-static)) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*.md))) \
	input/scholar/$$*/format-lecture.tex \
	input/scholar/$$*/pdf-prerequisites
	$(call doubletex,scholar)

.PHONY:
