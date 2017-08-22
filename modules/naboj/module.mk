MAKEFLAGS += --no-builtin-rules

.SECONDEXPANSION:

input/seminar/%/pdf-prerequisites: \
	$$(subst source/,input/,$$(wildcard source/input/$$*/*/*.jpg)) \
	$$(subst source/,input/,$$(wildcard source/input/$$*/*/*.png)) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/input/$$*/*/*.svg))) \
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/input/$$*/*/*.gp))) \
	$$(wildcard source/input/$$*/*/meta.yaml) \
	source/input/$$*/meta.yaml ;
	
output/naboj/%/booklet.pdf:\
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/problem.tex))\
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/solution.tex))\
	$$(wildcard source/seminar/$$*/*/meta.yaml) \
	input/naboj/%/pdf-prerequisites \
	source/naboj/$$*/meta.yaml ;
	input/naboj/$$*/intro.tex\
	input/naboj/$$*/prepare
	mkdir -p $(dir $@)
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=output/$*/booklet-single -halt-on-error -interaction=nonstopmode core/templates/booklet.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=output/$*/booklet-single -halt-on-error -interaction=nonstopmode core/templates/booklet.tex
	pdfbook --short-edge --outfile $@ output/$*/booklet-single.pdf

