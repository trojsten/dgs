MAKEFLAGS += --no-builtin-rules

.SECONDEXPANSION:

input/naboj/%/templates: \
	$$(wildcard source/naboj/$$*/*/meta.yaml) \
	source/naboj/$$*/../meta.yaml 
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	./modules/naboj/build.py 'source/naboj/' $(word 1,$(words)) $(word 2,$(words)) $(word 3,$(words)) -o '$(dir $@)'

input/naboj/%/booklet.tex: input/naboj/templates
input/naboj/%/answers.tex: input/naboj/templates
input/naboj/%/tearoff.tex: input/naboj/templates
input/naboj/%/format.tex: input/naboj/templates

input/naboj/%/pdf-prerequisites: \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.jpg)) \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.png)) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/*/*.svg))) \
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/*/*.gp))) \
	$$(wildcard source/naboj/$$*/*/meta.yaml) \
	source/naboj/$$*/../meta.yaml \
	input/naboj/$$*/format.tex ;
	
output/naboj/%/booklet.pdf:\
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/problem.md))) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/solution.md))) \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/templates
	mkdir -p $(dir $@)
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=output/naboj/$*/booklet -halt-on-error -interaction=nonstopmode input/naboj/$*/booklet.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=output/naboj/$*/booklet -halt-on-error -interaction=nonstopmode input/naboj/$*/booklet.tex
#	pdfbook --short-edge --outfile $@ output/$*/booklet-s.pdf

