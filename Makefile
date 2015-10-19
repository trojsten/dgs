all:				pdf html
debug:				pdf html

pdf:				collect output/tasks.pdf output/solutions.pdf
html:				collect
	@echo -e '\e[33mWarning: HTML not yet implemented\e[0m'
tasks:				output/tasks.pdf
solutions:			output/solutions.pdf	

textasks =			$(wildcard source/tasks/*.tex)
texsolutions =		$(wildcard source/solutions/*.tex)
tex-tasks:			$(patsubst source%, input%, $(textasks))
tex-solutions:		$(patsubst source%, input%, $(texsolutions))
texs:				tex-tasks tex-solutions

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



install:
	mkdir -p ~/texmf/tex/latex/local/dgs/
	cp *.sty ~/texmf/tex/latex/local/dgs/

collect:
	@echo -e '\e[32mCreating input folder hierarchy\e[0m'
	mkdir -p input/ input/tasks/ input/solutions/
	mkdir -p temp/
	mkdir -p output/
	cp source/current.tex input/current.tex

tasks-html:	
	@echo HTML not yet implemented

solutions-html: ;
	@echo -e '\e[33mWarning: HTML output is currently not implemented\e[0m'

input/tasks/%.tex: source/tasks/%.tex
	cp $< $@

input/tasks/%.pdf: source/tasks/%.svg
	@echo -e '\e[32mConverting $< to PDF:\e[0m'
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@ $@-crop
	mv $@-crop $@

input/tasks/%.pdf: source/tasks/%.gp
	cd source/tasks/ ; gnuplot $(notdir $<) ; cd ../../
	mv $(patsubst %.gp, %.pdf, $<) $@

input/tasks/%.pdf: source/tasks/%.pdf
	cp $< $@

input/tasks/%.png: source/tasks/%.png
	cp $< $@

input/solutions/%.tex: source/solutions/%.tex
	cp $< $@

input/solutions/%.pdf: source/solutions/%.svg
	@echo -e '\e[32mConverting $< to PDF:\e[0m'
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@ $@-crop
	mv $@-crop $@

input/solutions/%.pdf: source/solutions/%.gp
	cd source/solutions/ ; gnuplot $(notdir $<) ; cd ../../
	mv $(patsubst %.gp, %.pdf, $<) $@

input/solutions/%.pdf: source/solutions/%.pdf
	cp $< $@

input/solutions/%.png: source/solutions/%.png
	cp $< $@

input/tasks/%.png: source/tasks/%.svg
	@echo -e '\e[31mPNG output is currently not implemented\e[0m'

output/tasks.pdf: svg-to-pdf gp-to-pdf copy-png tasks.tex tex-tasks
	@echo -e '\e[32m$@: XeLaTeX primary run\e[0m'
	xelatex -jobname=output/tasks -halt-on-error tasks.tex 
	@echo -e '\e[32m$@: XeLaTeX secondary run (to get the cross-references right)\e[0m'
	xelatex -jobname=output/tasks -halt-on-error tasks.tex

output/solutions.pdf: svg-to-pdf gp-to-pdf copy-png solutions.tex tex-solutions
	@echo -e '\e[32m$@: XeLaTeX primary run\e[0m'
	xelatex -jobname=output/solutions -halt-on-error solutions.tex
	@echo -e '\e[32m$@: XeLaTeX secondary run (to get the cross-references right)\e[0m'
	xelatex -jobname=output/solutions -halt-on-error solutions.tex

output/tasks/%.pdf: input/tasks/%.tex svg-to-pdf
	@echo -e '\e[32mRendering single task $@\e[0m'
	cp singletask.tex temp/singletask.tex
	sed -i 's#@filename@#$<#g' temp/singletask.tex
	TASK=`echo '$(notdir $@)' | tr -cd 0-9` ; sed -i "s#@tasknumber@#$$TASK#g" temp/singletask.tex
	xelatex -jobname=$(basename $@) -halt-on-error temp/singletask.tex
	xelatex -jobname=$(basename $@) -halt-on-error temp/singletask.tex
	pdfcrop $@ $@-crop
	mv $@-crop $@
	rm temp/singletask.tex

view-tasks: tasks
	evince output/tasks.pdf 2>/dev/null 1>/dev/null &

view-solutions: solutions
	evince output/solutions.pdf 2>/dev/null 1>/dev/null &

clean:
	@echo Clean:
	rm -rf input/ temp/
	find . -type f \( -name "*.log" -or -name "*.aux" -or -name "*~" -or -name "*.out" -or -name "*.swp" \) -delete	

distclean: clean
	@echo Dist clean:
	rm -rf output/

.PHONY:
