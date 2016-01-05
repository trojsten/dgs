all:				hello pdf html
debug:				hello pdf html

pdf:				collect output/tasks.pdf output/solutions.pdf
html:				collect
	@echo -e '\e[33mWarning: HTML not yet implemented\e[0m'
tasks:				output/tasks.pdf
solutions:			output/solutions.pdf	

version	=			'0.32'
date =				'2015-12-12'
texs =				$(wildcard source/tasks/*.tex) $(wildcard source/solutions/*.tex)
copy-tex:			$(patsubst source%, input%, $(texs))

svgs =				$(wildcard source/tasks/*.svg) $(wildcard source/solutions/*.svg)
svg-to-pdf:			$(patsubst %.svg, %.pdf, $(patsubst source%, input%, $(svgs)))
svg-to-png:			$(patsubst %.svg, %.png, $(patsubst source%, input%, $(svgs)))

gps =				$(wildcard source/tasks/*.gp) $(wildcard source/solutions/*.gp)
gp-to-pdf:			$(patsubst %.gp, %.pdf, $(patsubst source%, input%, $(gps)))
gp-to-png:			$(patsubst %.gp, %.png, $(patsubst source%, input%, $(gps)))

pdfs =				$(wildcard source/tasks/*.pdf) $(wildcard source/solutions/*.pdf)
copy-pdf:			$(patsubst source%, input%, $(pdfs))

pngs =				$(wildcard source/tasks/*.png) $(wildcard source/solutions/*.png)
copy-png:			$(patsubst source%, input%, $(pngs))

hello:
	@echo -e '\e[32mThis is DeGeŠ, version \e[95m$(version)\e[32m (\e[95m$(date)\e[32m)\e[0m'

install:
	mkdir -p ~/texmf/tex/latex/local/dgs/
	cp *.sty ~/texmf/tex/latex/local/dgs/

collect:
	@echo -e '\e[32mCreating input folders\e[0m'
	mkdir -p input/ input/tasks/ input/solutions/
	mkdir -p output/
	cp source/current.tex input/current.tex

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
	cp $< $@

input/%.png: source/%.png
	@echo -e '\e[32mCopying PNG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

input/%.png: source/%.svg
	@echo -e '\e[31mSVG to PNG conversion is currently not implemented\e[0m'

output/%.pdf: collect svg-to-pdf gp-to-pdf copy-png copy-tex $(subst output/,,$(subst pdf,tex,$@)) 
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode $*.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run (to get the cross-references right)\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode $*.tex

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
	rm -rf input/ temp/
	find . -type f \( -name "*.log" -or -name "*.aux" -or -name "*~" -or -name "*.out" -or -name "*.swp" \) -delete	

distclean: clean
	@echo -e '\e[32mDist clean:\e[0m'
	rm -rf output/
