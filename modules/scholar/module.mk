.SECONDEXPANSION:

input/scholar/%/build-handout: \
	modules/scholar/format-handout.tex \
	modules/scholar/templates/handout.tex \
    source/scholar/$$*/meta.yaml
	@echo -e '$(c_action)Building handout for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/scholar/build-handout.py 'source/scholar/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/scholar/%/format-handout.tex: \
	input/scholar/$$*/build-handout ;

input/scholar/%/handout.tex: \
	input/scholar/$$*/build-handout ;

input/scholar/%/pdf-prerequisites: \
	$$(subst source/,input/,$$(wildcard source/scholar/$$*/*.jpg)) \
	$$(subst source/,input/,$$(wildcard source/scholar/$$*/*.png)) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/scholar/$$*/*.svg))) \
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/scholar/$$*/*.gp))) \
	source/scholar/$$*/meta.yaml ;

output/scholar/%/handout.pdf: \
	$$(subst $$(cdir),,$$(abspath input/scholar/$$*/../../../copy-static)) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*.md))) \
	input/scholar/$$*/handout.tex \
	input/scholar/$$*/format-handout.tex \
	input/scholar/$$*/pdf-prerequisites
	@mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), primary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/scholar/$*/handout.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), secondary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/scholar/$*/handout.tex

input/scholar/%/build-homework: \
	modules/scholar/format-homework.tex \
	modules/scholar/templates/homework.tex
	@echo -e '$(c_action)Building homework for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/scholar/build-homework.py 'source/scholar/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/scholar/%/format-homework.tex: \
	input/scholar/$$*/build-homework ;

input/scholar/%/homework.tex: \
	input/scholar/$$*/build-homework ;

output/scholar/%/homework.pdf: \
	$$(subst $$(cdir),,$$(abspath input/scholar/$$*/../../../copy-static)) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*.md))) \
	input/scholar/$$*/homework.tex \
	input/scholar/$$*/format-homework.tex
	@mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), primary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/scholar/$*/homework.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), secondary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/scholar/$*/homework.tex

.PHONY:
