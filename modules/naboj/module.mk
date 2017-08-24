MAKEFLAGS += --no-builtin-rules

.SECONDEXPANSION:

input/naboj/%/format.tex: \
	modules/naboj/format.tex \
	source/naboj/$$*/../meta.yaml 
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	./modules/naboj/build.py 'source/naboj/' $(word 1,$(words)) $(word 2,$(words)) $(word 3,$(words)) -o '$(dir $@)'

input/naboj/%/booklet.tex input/naboj/%/answers.tex input/naboj/%/tearoff.tex: \
	modules/naboj/templates/$$(notdir $@) \
	source/naboj/$$*/../meta.yaml 
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	./modules/naboj/build.py 'source/naboj/' $(word 1,$(words)) $(word 2,$(words)) $(word 3,$(words)) -o '$(dir $@)'

input/naboj/%/pdf-prerequisites: \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.jpg)) \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.png)) \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.pdf)) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/*/*.svg))) \
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/*/*.gp))) \
	$$(wildcard source/naboj/$$*/*/meta.yaml) \
	source/naboj/$$*/../meta.yaml ;
	
output/naboj/%/booklet.pdf: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/problem.md))) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/solution.md))) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/answer.md))) \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/format.tex \
	input/naboj/%/booklet.tex 
	mkdir -p $(dir $@)
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=output/naboj/$*/booklet -halt-on-error -interaction=nonstopmode input/naboj/$*/booklet.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=output/naboj/$*/booklet -halt-on-error -interaction=nonstopmode input/naboj/$*/booklet.tex

output/naboj/%/booklet-print.pdf: \
	output/naboj/%/booklet.pdf
	pdfbook --short-edge --quiet --outfile $@ $<

output/naboj/%/answers.pdf: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/answer.md))) \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/answers.tex 
	mkdir -p $(dir $@)
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/answers.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/answers.tex

output/naboj/%/tearoff.pdf: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/problem.md))) \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/tearoff.tex 
	mkdir -p $(dir $@)
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/tearoff.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/tearoff.tex
