all:				hello pdf html
debug:				hello pdf html

pdf:				collect output/tasks.pdf output/solutions.pdf
html:				collect md-to-html svg-to-png
tasks:				output/tasks.pdf
solutions:			output/solutions.pdf	

version	=			'0.39'
date =				'2016-02-11'

mds =				$(wildcard temp/tasks/*.md) $(wildcard temp/solutions/*.md)
md-to-tex:			$(patsubst %.md, %.tex, $(patsubst temp%, input%, $(mds)))
md-to-html:			$(patsubst %.md, %.html, $(patsubst temp%, output%, $(mds)))

svgs =				$(wildcard temp/graphics/*.svg)
svg-to-pdf:			$(patsubst %.svg, %.pdf, $(patsubst temp%, input%, $(svgs)))
svg-to-png:			$(patsubst %.svg, %.png, $(patsubst temp%, output%, $(svgs)))

gps =				$(wildcard temp/graphics/*.gp)
gp-to-pdf:			$(patsubst %.gp, %.pdf, $(patsubst temp%, input%, $(gps)))
gp-to-png:			$(patsubst %.gp, %.png, $(patsubst temp%, input%, $(gps)))

pdfs =				$(wildcard temp/graphics/*.pdf)
copy-pdf:			$(patsubst temp%, input%, $(pdfs))

pngs =				$(wildcard temp/graphics/*.png)
copy-png:			$(patsubst temp%, input%, $(pngs))

jpgs =				$(wildcard temp/graphics/*.jpg)
copy-jpg:			$(patsubst temp%, input%, $(jpgs))

hello:
	@echo -e '\e[32mThis is DeGeŠ, version \e[95m$(version)\e[32m (\e[95m$(date)\e[32m)\e[0m'

collect:
	@echo -e '\e[32mCreating input folders (unless they are already present)\e[0m'
	mkdir -p input/ input/tasks/ input/solutions/ input/graphics/
	mkdir -p output/ output/tasks/ output/solutions/ output/graphics/

input/%.tex: temp/%.md
	@echo -e '\e[32mConverting Markdown file \e[96m$<\e[32m to TeX:\e[0m'
	./core/dgs-convert.sh $< $@
	vlna -l -r -v KkSsVvZzOoUuAaIi $@

input/%.tex: temp/%.tex
	@echo -e '\e[32mCopying TeX source file \e[96m$<\e[32m:\e[0m'
	cp $< $@

input/%.pdf: temp/%.svg
	@echo -e '\e[32mConverting \e[96m$<\e[32m to PDF:\e[0m'
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@ $@-crop
	mv $@-crop $@

input/%.pdf: temp/%.gp
	@echo -e '\e[32mConverting gnuplot file \e[96m$<\e[32m to PDF:\e[0m'
	cd $(<D) ; gnuplot -e "set terminal pdf font 'Verdana, 12'; set output '../../$@'" $(notdir $<)

input/%.pdf: temp/%.pdf
	@echo -e '\e[32mCopying PDF file \e[96m$<\e[32m:\e[0m'
	cp $< $@

input/%.png: temp/%.png
	@echo -e '\e[32mCopying PNG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

input/%.jpg: temp/%.jpg
	@echo -e '\e[32mCopying JPG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

output/%.png: temp/%.svg
	@echo -e '\e[32mConverting SVG file \e[96m$<\e[32m to PNG\e[0m'
	rsvg-convert -f png -h 250 -a -o $@ $<

output/%.png: temp/%.png
	@echo -e '\e[32mCopying PNG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

output/%.jpg: temp/%.jpg
	@echo -e '\e[32mCopying JPG image \e[96m$<\e[32m:\e[0m'
	cp $< $@


output/%.html: temp/%.md
	@echo -e '\e[32mConverting Markdown file \e[96m$<\e[32m to HTML:\e[0m'
	./core/dgs-convert.sh $< $@

# temp/fks/31/spring/1/output/tasks/01.html
# temp/fks/31/spring/1/temp/tasks/01.md

output/%.pdf: collect svg-to-pdf gp-to-pdf copy-png copy-jpg md-to-tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/$*.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run (to get the cross-references right)\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/$*.tex



#output/tasks/%.pdf: input/tasks/%.tex svg-to-pdf
#	@echo -e '\e[32mRendering single task $@\e[0m'
#	cp singletask.tex temp/singletask.tex
#	sed -i 's#@filename@#$<#g' temp/singletask.tex
#	TASK=`echo '$(notdir $@)' | tr -cd 0-9` ; sed -i "s#@tasknumber@#$$TASK#g" temp/singletask.tex
#	xelatex -jobname=$(basename $@) -halt-on-error temp/singletask.tex
#	xelatex -jobname=$(basename $@) -halt-on-error temp/singletask.tex
#	pdfcrop $@ $@-crop
#	mv $@-crop $@
#	rm temp/singletask.tex

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

