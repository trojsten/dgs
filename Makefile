all:				collect pdf html clean
debug:				collect pdf html

pdf:				output/tasks.pdf output/solutions.pdf
#html:           pictures-png tasks-html solutions-html
html:
	@echo -e '\e[33mWarning: HTML not yet implemented\e[0m'
tasks:				output/tasks.pdf
solutions:			output/solutions.pdf	

tex-tasks-s =		$(wildcard source/tasks/*.tex)
tex-solutions-s =	$(wildcard source/solutions/*.tex)
tex-tasks:			$(patsubst source%, input%, $(tex-tasks-s))
tex-solutions:		$(patsubst source%, input%, $(tex-solutions-s))
texs:				tex-tasks tex-solutions

svgs =				$(wildcard source/tasks/*.svg) $(wildcard source/solutions/*.svg)
svg-to-pdf:			$(patsubst %.svg, %.pdf, $(patsubst source%, input%, $(svgs)))
svg-to-png:			$(patsubst %.svg, %.png, $(patsubst source%, input%, $(svgs)))

gps =				$(wildcard source/tasks/*.gp) $(wildcard source/solutions/*.gp)
gp-to-pdf:			$(patsubst %.gp, %.pdf, $(gps))
gp-to-png:			$(patsubst %.gp, %.png, $(gps))

pdfs =				$(wildcard source/tasks/i*.pdf) $(wildcard source/solutions/*.pdf)
copy-pdf:			$(patsubst source%, input%, $(pdfs))

pngs =				$(wildcard source/tasks/i*.png) $(wildcard source/solutions/*.png)
copy-png:			$(patsubst source%, input%, $(pngs))



install:
	mkdir -p ~/texmf/tex/latex/local/dgs/
	cp *.sty ~/texmf/tex/latex/local/dgs/

collect:
	mkdir -p input/ input/tasks/ input/solutions/
	mkdir -p output
	cp source/current.tex input/current.tex

gnuplot:        gnuplot-pdf gnuplot-png
gnuplot-pdf:
	@echo -e '\e[32mConverting all gnuplot (.gp) files to .pdf\e[0m'
	cd input/tasks/; \
		find . -type f -name "*.gp" -exec gnuplot {} \;
	cd input/solutions/; \
		find . -type f -name "*.gp" -exec gnuplot {} \;

gnuplot-png:
	@echo -e '\e[33mWarning: Gnuplot PNG is currently not implemented\e[0m'

	

tasks-html:	
	@echo HTML not yet implemented

solutions-html: ;
	@echo -e '\e[33mWarning: HTML output is currently not implemented\e[0m'

input/tasks/%.tex: source/tasks/%.tex
	cp $< $@

input/tasks/%.pdf: source/tasks/%.svg
	@echo Converting $< to PDF:
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@

input/tasks/%.pdf: source/tasks/%.gp
	./dgs-gnuplot $< $@

input/tasks/%.pdf: source/tasks/%.pdf
	cp $< $@

input/tasks/%.png: source/tasks/%.png
	cp $< $@

input/solutions/%.tex: source/solutions/%.tex
	cp $< $@

input/solutions/%.pdf: source/solutions/%.svg
	@echo Converting $< to PDF:
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@

input/solutions/%.pdf: source/solutions/%.pdf
	cp $< $@

input/solutions/%.png: source/solutions/%.png
	cp $< $@

input/tasks/%.png: source/tasks/%.svg
	@echo -e '\e[31mPNG output is currently not implemented\e[0m'

output/tasks.pdf: svg-to-pdf copy-pdf copy-png tasks.tex tex-tasks
	@echo -e '\e[32m$@: XeLaTeX primary run\e[0m'
	xelatex -jobname=output/tasks -halt-on-error tasks.tex 
	@echo -e '\e[32m$@: XeLaTeX second run (to get the cross-references right)\e[0m'
	xelatex -jobname=output/tasks -halt-on-error tasks.tex

output/solutions.pdf: svg-to-pdf copy-pdf copy-png solutions.tex tex-solutions
	@echo -e '\e[32m$@: XeLaTeX primary run\e[0m'
	xelatex -jobname=output/solutions -halt-on-error solutions.tex
	@echo -e '\e[32m$@: XeLaTeX second run (to get the cross-references right)\e[0m'
	xelatex -jobname=output/solutions -halt-on-error solutions.tex



view-tasks: tasks
	evince output/tasks.pdf 2>/dev/null 1>/dev/null &

view-solutions: solutions
	evince output/solutions.pdf 2>/dev/null 1>/dev/null &

clean:
	@echo Clean:
	rm -rf input/
	find . -type f \( -name "*.log" -or -name "*.aux" -or -name "*~" -or -name "*.out" -or -name "*.swp" \) -delete	

distclean: clean
	@echo Dist clean:
	rm -rf output/

.PHONY: clean distclean tasks solutions tasks.pdf solutions.pdf pictures-pdf all tex-tasks
