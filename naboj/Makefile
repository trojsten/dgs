.SECONDARY:

version =           '1.26'
date =              '2016-11-01'

hello:
	@echo -e '\e[32mThis is DeGeŠ Makefile, version \e[95m$(version)\e[32m [\e[95m$(date)\e[32m]\e[0m'

input/%.tex: source/%.tex
	@echo -e '\e[32mCopying TeX file \e[96m$<\e[0m'
	mkdir -p $(dir $@)
	./core/dgs-convert.py ${language} $< $@ || exit 1;
	vlna -l -r -v KkSsVvZzOoUuAaIi $@

input/%.pdf: source/%.svg
	@echo -e '\e[32mConverting SVG file \e[96m$<\e[32m to PDF:\e[0m'
	mkdir -p $(dir $@)
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@ $@-crop
	mv $@-crop $@

input/%.pdf: source/%.pdf
	@echo -e '\e[32mCopying PDF file \e[96m$<\e[32m:\e[0m'
	cp $< $@

input/%.png: source/%.png
	@echo -e '\e[32mCopying PNG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

input/%.jpg: source/%.jpg
	@echo -e '\e[32mCopying JPG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

.SECONDEXPANSION:

corefiles:\
	core/*\
	core/config/*

input/%/prepare: core/dgs-prepare.py\
	source/$$(dir $$*)settings.json
	mkdir -p $(dir $@)
	@echo -e '\e[32mPreparing recipes\e[0m'
	./core/dgs-prepare.py $(language) ./source/$(dir $*)settings.json

input/%/barcodes.txt: input/%/prepare ;

input/%/barcodes.pdf: input/%/barcodes.txt
	@echo -e '\e[32mCreating barcode PDF file \e[96m$@\e[32m:\e[0m'
	barcode -e "128" -i input/$*/barcodes.txt -g "120x30" -p "120x30mm" -n -o input/$*/barcodes.ps
	ps2pdf input/$*/barcodes.ps input/$*/barcodes-big.pdf
	pdfcrop input/$*/barcodes-big.pdf $@

output/%/answers.pdf:\
	corefiles\
	$$(subst source/,input/,$$(wildcard source/$$*/*/answer.tex))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.jpg))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.png))\
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/$$*/*/*.svg)))\
	input/$$*/prepare
	mkdir -p $(dir $@)
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/answers.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/answers.tex

output/%/booklet.pdf:\
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

output/%/tearoff.pdf:\
	corefiles\
	$$(subst source/,input/,$$(wildcard source/$$*/*/problem.tex))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.jpg))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.png))\
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/$$*/*/*.svg)))\
	input/$$*/barcodes.pdf	
	mkdir -p $(dir $@)
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/tearoff.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/tearoff.tex

output/%/instructions.pdf:\
	corefiles\
	input/$$*/instructions.tex\
	input/$$*/constants.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/instructions.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/instructions.tex

output/%/cover.pdf:\
	corefiles
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/cover.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/cover.tex

   
output/%/all: output/%/booklet.pdf output/%/answers.pdf output/%/tearoff.pdf output/%/instructions.pdf output/%/cover.pdf ;

clean:
	@echo -e '\e[32mClean:\e[0m'
	rm -rf input/

distclean: clean
	@echo -e '\e[32mDist clean:\e[0m'
	rm -rf temp/
	rm -rf output/

