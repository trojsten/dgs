.SECONDARY:

version =           '1.14'
date =              '2016-10-14'

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

input/%/prepare: core/dgs-prepare.py\
	source/$$(dir $$*)settings.json
	mkdir -p $(dir $@)
	@echo -e '\e[32mPreparing recipes\e[0m'
	./core/dgs-prepare.py $(language) ./source/$(dir $*)settings.json

input/%/barcodes.txt: input/%/prepare ;

input/%/barcodes.pdf: input/%/barcodes.txt
	@echo -e '\e[32mCreating barcode PDF file\e[0m'
	barcode -e "39" -i input/$*/barcodes.txt -g "100x25" -p "100x25mm" -o input/$*/barcodes.ps
	ps2pdf input/$*/barcodes.ps input/$*/barcodes-big.pdf
	pdfcrop input/$*/barcodes-big.pdf $@

output/%/answers.pdf:\
	$$(subst source/,input/,$$(wildcard source/$$*/*/answer.tex))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.jpg))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.png))\
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/$$*/*/*.svg)))\
	core/dgs.sty\
	input/$$*/prepare
	mkdir -p $(dir $@)
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/answers.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/answers.tex

output/%/booklet.pdf:\
	$$(subst source/,input/,$$(wildcard source/$$*/*/problem.tex))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/solution.tex))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.jpg))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.png))\
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/$$*/*/*.svg)))\
	core/dgs.sty\
	input/$$*/prepare
	mkdir -p $(dir $@)
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/booklet.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/booklet.tex

output/%/tearoff.pdf:\
	$$(subst source/,input/,$$(wildcard source/$$*/*/problem.tex))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.jpg))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.png))\
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/$$*/*/*.svg)))\
	core/dgs.sty\
	input/$$*/barcodes.pdf	
	mkdir -p $(dir $@)
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/tearoff.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/tearoff.tex
   
output/%/all: output/%/booklet.pdf output/%/answers.pdf output/%/tearoff.pdf ;

clean:
	@echo -e '\e[32mClean:\e[0m'
	rm -rf input/

distclean: clean
	@echo -e '\e[32mDist clean:\e[0m'
	rm -rf temp/
	rm -rf output/

