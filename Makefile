all:				hello

.SECONDARY:

version	=			'1.53'
date =				'2016-11-29'

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
	@echo -e '\e[32mConverting \e[96m$<\e[32m to PDF file \e[96m$@\e[32m:\e[0m'
	mkdir -p $(dir $@)
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@ $@-crop
	mv $@-crop $@

input/%.pdf: input/%.gp
	@echo -e '\e[32mBuilding gnuplot file \e[96m$<\e[32m to PDF file \e[96m$@\e[32m:\e[0m'
	mkdir -p $(dir $@)
	cd $(dir $@); gnuplot -e "set terminal pdf font 'TeX Gyre Pagella, 12'; set output '$(notdir $@)'" $(notdir $<)

input/%.pdf: source/%.pdf
	@echo -e '\e[32mCopying PDF file \e[96m$<\e[32m:\e[0m'
	mkdir -p $(dir $@)
	cp $< $@

input/%.png: source/%.png
	@echo -e '\e[32mCopying PNG image \e[96m$<\e[32m:\e[0m'
	mkdir -p $(dir $@)
	cp $< $@

input/%.jpg: source/%.jpg
	@echo -e '\e[32mCopying JPG image \e[96m$<\e[32m:\e[0m'
	mkdir -p $(dir $@)
	cp $< $@

input/%.dat: source/%.dat
	@echo -e '\e[32mCopying data file \e[96m$<\e[32m to file \e[96m$@\e[32m:\e[0m'
	mkdir -p $(dir $@)
	cp $< $@

output/%.png: source/%.svg
	@echo -e '\e[32mConverting SVG file \e[96m$<\e[32m to PNG file \e[96m$@\e[32m:\e[0m'
	mkdir -p $(dir $@)
	rsvg-convert -f png -h 300 -a -o $@ $<

output/%.png: source/%.png
	@echo -e '\e[32mCopying PNG image \e[96m$<\e[32m:\e[0m'
	mkdir -p $(dir $@)
	cp $< $@

output/%.png: source/%.gp
	@echo -e '\e[32mConverting gnuplot file \e[96m$<\e[32m to PNG:\e[0m'
	mkdir -p $(dir $@)
	cd $(subst output/,input/,$(dir $@)); gnuplot -e "set terminal png font 'TeX Gyre Pagella, 12'; set output '$(notdir $@)'" "../../../../../../"$<

output/%.jpg: source/%.jpg
	@echo -e '\e[32mCopying JPG image \e[96m$<\e[32m:\e[0m'
	mkdir -p $(dir $@)
	cp $< $@

output/%.html: source/%.md
	@echo -e '\e[32mConverting Markdown file \e[96m$<\e[32m to HTML file \e[96m$@\e[32m:\e[0m'
	mkdir -p $(dir $@)
	./core/dgs-convert.py html $< $@ || exit 1;

.SECONDEXPANSION:
input/%.gp:\
	source/%.gp\
	$$(subst source/,input/,$$(wildcard $$(dir source/%.gp)*.dat))
	@mkdir -p $(dir $@)
	@echo -e '\e[32mCopying gnuplot file \e[96m$<\e[32m:\e[0m'
	cp $< $@

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
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/problems.tex

output/%/solutions.pdf:\
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/$$*/*/problem.md)))\
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/$$*/*/solution.md)))\
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/$$*/*/*.svg)))\
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/$$*/*/*.gp)))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.jpg))\
	$$(subst source/,input/,$$(wildcard source/$$*/*/*.png))\
	source/%/settings.json
	mkdir -p $(dir $@)
	./core/dgs-prepare.py ./source/$*/settings.json
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/solutions.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/solutions.tex

output/%/html-problems:\
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/$$*/*/problem.md)))\
	$$(subst source/,output/,$$(subst .svg,.png,$$(wildcard source/$$*/*/*.svg))) ;

output/%/html-solutions:\
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/$$*/*/solution.md)))\
	$$(subst source/,output/,$$(subst .svg,.png,$$(wildcard source/$$*/*/*.svg)))\
	$$(subst source/,output/,$$(subst .gp,.png,$$(wildcard source/$$*/*/*.gp))) ;

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

