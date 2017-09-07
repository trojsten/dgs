MAKEFLAGS += --no-builtin-rules

.SECONDEXPANSION:

input/%/invite.tex: 
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/invite/build.py 'source/' $(word 1,$(words)) $(word 2,$(words)) $(word 3,$(words)) -o '$(dir $@)'

output/%/invite.pdf:\
	input/$$*/invite.tex\
	source/%/meta.yaml
	@mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), primary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/$*/invite.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), secondary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/$*/invite.tex

%/all: \
	$$*/booklet.pdf \
	$$*/answers.pdf ;

%/all: \
	$$*/tearoff.pdf ;
