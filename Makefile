all:				hello

.SECONDARY:

version	=			'1.05'
date =				'2016-09-24'

hello:
	@echo -e '\e[32mThis is DeGeŠ Makefile, version \e[95m$(version)\e[32m [\e[95m$(date)\e[32m]\e[0m'

input/%.tex: source/%.md
	@echo -e '\e[32mConverting Markdown file \e[96m$<\e[32m to TeX file \e[96m$@\e[32m:\e[0m'
	mkdir -p $(dir $@)
	./core/dgs-convert.py latex $< $@ || exit 1;
	vlna -l -r -v KkSsVvZzOoUuAaIi $@

input/%.tex: source/%.tex
	@echo -e '\e[32mCopying TeX source file \e[96m$<\e[32m:\e[0m'
	mkdir -p $(dir $@)
	cp $< $@

input/%.pdf: source/%.svg
	@echo -e '\e[32mConverting \e[96m$<\e[32m to PDF:\e[0m'
	mkdir -p $(dir $@)
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@ $@-crop
	mv $@-crop $@

input/%.pdf: source/%.gp
	@echo -e '\e[32mConverting gnuplot file \e[96m$<\e[32m to PDF:\e[0m'
	mkdir -p $(dir $@)
	cd $(<D) ; gnuplot -e "set terminal pdf font 'Verdana, 12'; set output '../../$@'" $(notdir $<)

input/%.pdf: source/%.pdf
	@echo -e '\e[32mCopying PDF file \e[96m$<\e[32m:\e[0m'
	cp $< $@

input/%.png: source/%.png
	@echo -e '\e[32mCopying PNG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

input/%.jpg: source/%.jpg
	@echo -e '\e[32mCopying JPG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

output/%.png: source/%.svg
	@echo -e '\e[32mConverting SVG file \e[96m$<\e[32m to PNG\e[0m'
	rsvg-convert -f png -h 250 -a -o $@ $<

output/%.png: source/%.png
	@echo -e '\e[32mCopying PNG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

output/%.png: source/%.gp
	@echo -e '\e[32mConverting gnuplot file \e[96m$<\e[32m to PNG:\e[0m'
	cd $(<D) ; gnuplot -e "set terminal png transparent truecolor font 'Verdana, 12'; set output '../../$@'" $(notdir $<)

output/%.jpg: source/%.jpg
	@echo -e '\e[32mCopying JPG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

output/%.html: source/%.md
	@echo -e '\e[32mConverting Markdown file \e[96m$<\e[32m to HTML file \e[96m$@\e[32m:\e[0m'
	mkdir -p $(dir $@)
	./core/dgs-convert.py html $< $@ || exit 1;

.SECONDEXPANSION:

output/%/problems.pdf:\
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/$$*/*/problem.md)))\
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/$$*/*/*.svg)))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.jpg))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.png))\
	source/%/settings.json
	mkdir -p $(dir $@)
	./core/dgs-prepare.py ./source/$*/settings.json
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/problems.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run (to get the cross-references right)\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/problems.tex

output/%/solutions.pdf:\
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/$$*/*/problem.md)))\
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/$$*/*/solution.md)))\
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/$$*/*/*.svg)))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.jpg))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.png))\
	source/%/settings.json
	mkdir -p $(dir $@)
	./core/dgs-prepare.py ./source/$*/settings.json
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/solutions.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run (to get the cross-references right)\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/solutions.tex

output/%/html-problems: $$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/$$*/*/problem.md))) ;

output/%/html-solutions: $$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/$$*/*/solution.md))) ;

output/%/pdf: output/%/problems.pdf output/%/solutions.pdf ;

output/%/html: output/%/html-problems output/%/html-solutions ;

output/%/problems: output/%/problems.pdf output/%/html-problems ;

output/%/solutions: output/%/solutions.pdf output/%/html-solutions ;

output/%/all: output/%/pdf output/%/html ;

clean:
	@echo -e '\e[32mClean:\e[0m'
	rm -rf input/

distclean: clean
	@echo -e '\e[32mDist clean:\e[0m'
	rm -rf output/

.PHONY: clean distclean hello

