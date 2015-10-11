all: tasks solutions

install:
	mkdir -p ~/texmf/tex/latex/local/dgs/
	cp *.sty ~/texmf/tex/latex/local/dgs/

define makedirs
	mkdir -p output
	mkdir -p temp
endef

tasks: tasks.pdf

tasks.pdf:
	$(makedirs)
	xelatex -jobname=output/tasks -halt-on-error tasks.tex
	@#xelatex -jobname=output/tasks -halt-on-error tasks.tex

solutions: solutions.pdf

solutions.pdf:
	$(makedirs)
	xelatex -jobname=output/solutions -halt-on-error solutions.tex
	@#xelatex --shell-escape -jobname=output/solutions -halt-on-error solutions.tex

view-tasks: tasks
	evince output/tasks.pdf 2>/dev/null 1>/dev/null &

view-solutions: solutions
	evince output/solutions.pdf 2>/dev/null 1>/dev/null &

svgs = $(wildcard tasks/fks/*.svg)
svg-to-pdf: $(patsubst %.pdf, %.svg, $(svgs))

files/fks/tasks/%.pdf: files/fks/tasks/%.svg
	@echo Converting $< to PDF:
	rsvg-convert --format pdf --keep-aspect-ratio --output temp/$*.pdf $<

clean:
	@echo Clean:
	rm -rf input/
	find . -type f \( -name "*.log" -or -name "*.aux" -or -name "*~" -or -name "*.out" -or -name "*.swp" \) -delete	

distclean: clean
	@echo Dist clean:
	rm -rf output/

.PHONY: tasks solutions tasks.pdf solutions.pdf	
