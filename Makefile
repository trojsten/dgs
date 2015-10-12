all:            collect-pdf pdf html clean
debug:          collect-pdf pdf html

pdf:            pictures-pdf tasks-pdf solutions-pdf
#html:           pictures-png tasks-html solutions-html
html:
	@echo '\e[31mHTML not yet implemented\e[0m'
tasks:          pictures tasks-pdf tasks-html
solutions:      pictures solutions-pdf solutions-html

pictures:       pictures-png pictures-pdf
svgs			= $(wildcard source/tasks/*.svg) $(wildcard source/solutions/*.svg)
texs			= $(wildcard input/tasks/*.tex) $(wildcard input/solutions/*.tex)
pictures-pdf:	$(patsubst %.svg, %.pdf, $(patsubst source, input, $(svgs)))

graphs:			graphs-pdf graphs-png
graphs-pdf:
	find source/ -type f -name "*.gp" -exec gnuplot {} \;		
graphs-png:
	@echo '\e[33mPNG is currently not implemented'

install:
	mkdir -p ~/texmf/tex/latex/local/dgs/
	cp *.sty ~/texmf/tex/latex/local/dgs/

collect-pdf: create-directories
	@echo Collect for PDF:
	find source/tasks/ -type f -name "*.tex" -exec cp {} input/tasks/ \;
	find source/solutions/ -type f -name "*.tex" -exec cp {} input/solutions/ \;

collect-html: create-directories	
	@echo Collect for HTML:	

create-directories:
	mkdir -p input input/tasks/ input/solutions/
	mkdir -p output

gnuplot-pdf:i	
	@echo '\e[32mConverting all gnuplot (.gp) files to .pdf\e[0m'


	

tasks-pdf: 
	@echo 'XeLaTeX first run'
	xelatex -jobname=output/tasks -halt-on-error tasks.tex 
	@echo 'XeLaTeX second run (to get the cross-references right)'
	xelatex -jobname=output/tasks -halt-on-error tasks.tex

tasks-html:	
	@echo HTML not yet implemented

solutions-pdf: 
	@echo 'XeLaTeX first run'
	xelatex -jobname=output/solutions -halt-on-error solutions.tex
	@echo 'XeLaTeX second run (to get the cross-references right)'
	xelatex -jobname=output/solutions -halt-on-error solutions.tex

solutions-html: ;
	@echo '\e[31mHTML output is currently not implemented\e[0m'

input/solutions/%.pdf: source/solutions/%.svg
	@echo Converting $< to PDF:
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<

input/tasks/%.pdf: source/tasks/%.svg
	@echo Converting $< to PDF:
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<

input/tasks/%.svg: source/tasks/%.svg
	cp $< $@

input/tasks/%.png: source/tasks/%.svg
	@echo TODO: png conversion

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

.PHONY: clean distclean tasks solutions tasks.pdf solutions.pdf create-directories pictures-pdf all
