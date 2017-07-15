MAKEFLAGS += --no-builtin-rules

.SUFFIXES:
	
module = naboj

output/$(module)/%/booklet.pdf:\
	corefiles\
	$$(subst source/,input/,$$(wildcard source/$$*/*/problem.tex))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/solution.tex))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.jpg))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.png))\
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/$$*/*/*.svg)))\
	input/$$*/intro.tex\
	input/$$*/prepare
	mkdir -p $(dir $@)
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=output/$*/booklet-single -halt-on-error -interaction=nonstopmode core/templates/booklet.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=output/$*/booklet-single -halt-on-error -interaction=nonstopmode core/templates/booklet.tex
	pdfbook --short-edge --outfile $@ output/$*/booklet-single.pdf

