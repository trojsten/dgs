.SECONDEXPANSION:

input/scholar/%/build-handout: \
	modules/scholar/format-handout.tex
	@echo -e '$(c_action)Building handout for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/scholar/build-handout.py 'source/scholar/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/scholar/%/format-handout.tex: \
	input/scholar/$$*/../build-handout ;

input/scholar/%/handout.tex: \
    input/scholar/$$*/build-handout ;

output/scholar/%/handout.pdf: \
	$$(subst $$(cdir),,$$(abspath input/scholar/$$*/../../../copy-static)) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/scholar/$$*/*.md))) \
	input/scholar/$$*/handout.tex \
	input/scholar/$$*/handout/format-handout.tex
	@mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), primary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/scholar/$*/handout.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), secondary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/scholar/$*/handout.tex

.PHONY:
