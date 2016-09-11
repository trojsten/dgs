all:				hello pdf html
debug:				hello pdf html

pdf:				tasks solutions
html:				md-to-html svg-to-png gp-to-png copy-pdf-out copy-png-out copy-jpg-out
tasks:				output/problems.pdf 
solutions:			output/solutions.pdf	

version	=			'1.00'
date =				'2016-09-08'

mds =				$(wildcard source/**/*.md)
md-to-tex:			$(patsubst %.md, %.tex, $(patsubst source%, input%, $(mds)))
md-to-html:			$(patsubst %.md, %.html, $(patsubst source%, output%, $(mds)))

svgs =				$(wildcard source/**/*.svg)
svg-to-pdf:			$(patsubst %.svg, %.pdf, $(patsubst source%, input%, $(svgs)))
svg-to-png:			$(patsubst %.svg, %.png, $(patsubst source%, output%, $(svgs)))

gps =				$(wildcard source/**/*.gp)
gp-to-pdf:			$(patsubst %.gp, %.pdf, $(patsubst source%, input%, $(gps)))
gp-to-png:			$(patsubst %.gp, %.png, $(patsubst source%, output%, $(gps)))

pdfs =				$(wildcard source/**/*.pdf)
copy-pdf:			$(patsubst source%, input%, $(pdfs))
copy-pdf-out:		$(patsubst source%, output%, $(pdfs))

pngs =				$(wildcard source/**/*.png)
copy-png:			$(patsubst source%, input%, $(pngs))
copy-png-out:		$(patsubst source%, output%, $(pngs))

jpgs =				$(wildcard source/**/*.jpg)
copy-jpg:			$(patsubst source%, input%, $(jpgs))
copy-jpg-out:		$(patsubst source%, output%, $(jpgs))

hello:
	@echo -e '\e[32mThis is DeGeŠ Makefile, version \e[95m$(version)\e[32m [\e[95m$(date)\e[32m]\e[0m'
    
input/%.tex: source/%.md
	@echo -e '\e[32mConverting Markdown file \e[96m$<\e[32m to TeX:\e[0m'
	./core/dgs-convert.py latex $< $@
	vlna -l -r -v KkSsVvZzOoUuAaIi $@

input/%.tex: source/%.tex
	@echo -e '\e[32mCopying TeX source file \e[96m$<\e[32m:\e[0m'
	cp $< $@

input/%.pdf: source/%.svg
	@echo -e '\e[32mConverting \e[96m$<\e[32m to PDF:\e[0m'
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@ $@-crop
	mv $@-crop $@

input/%.pdf: source/%.gp
	@echo -e '\e[32mConverting gnuplot file \e[96m$<\e[32m to PDF:\e[0m'
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
	@echo -e '\e[32mConverting gnuplot file \e[96mô<\e[32m to PNG:\e[0m'
	cd $(<D) ; gnuplot -e "set terminal png transparent truecolor font 'Verdana, 12'; set output '../../$@'" $(notdir $<)

output/%.jpg: source/%.jpg
	@echo -e '\e[32mCopying JPG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

output/%.html: source/%.md
	@echo -e '\e[32mConverting Markdown file \e[96m$<\e[32m to HTML:\e[0m'
	./core/dgs-convert.py html $< $@

output/%.pdf: svg-to-pdf gp-to-pdf copy-png copy-jpg md-to-tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/$*.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run (to get the cross-references right)\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/$*.tex


#output/tasks/%.pdf: input/tasks/%.tex svg-to-pdf
#	@echo -e '\e[32mRendering single task $@\e[0m'
#	cp singletask.tex source/singletask.tex
#	sed -i 's#@filename@#$<#g' source/singletask.tex
#	TASK=`echo '$(notdir $@)' | tr -cd 0-9` ; sed -i "s#@tasknumber@#$$TASK#g" source/singletask.tex
#	xelatex -jobname=$(basename $@) -halt-on-error source/singletask.tex
#	xelatex -jobname=$(basename $@) -halt-on-error source/singletask.tex
#	pdfcrop $@ $@-crop
#	mv $@-crop $@
#	rm source/singletask.tex

view-tasks: tasks
	evince output/tasks.pdf 2>/dev/null 1>/dev/null &

view-solutions: solutions
	evince output/solutions.pdf 2>/dev/null 1>/dev/null &

clean:
	@echo -e '\e[32mClean:\e[0m'
	rm -rf input/
	find . -type f \( -name "*.log" -or -name "*.aux" -or -name "*~" -or -name "*.out" -or -name "*.swp" \) -delete	

distclean: clean
	@echo -e '\e[32mDist clean:\e[0m'
	rm -rf output/

.PHONY: clean distclean
