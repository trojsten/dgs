all: tasks solutions view

define makedirs
	mkdir -p output
	mkdir -p temp
endef

tasks: tasks.pdf

tasks.pdf:
	$(makedirs)
	xelatex -jobname=output/tasks -halt-on-error tasks.tex
	#xelatex -jobname=output/tasks -halt-on-error tasks.tex

solutions: solutions.pdf

solutions.pdf:
	$(makedirs)
	xelatex -jobname=output/solutions -halt-on-error solutions.tex
	#xelatex -jobname=output/solutions -halt-on-error solutions.tex

view:
	evince output/solutions.pdf 2>/dev/null 1>/dev/null &

svgs = $(wildcard tasks/fks/*.svg)
svg-to-pdf: $(patsubst %.pdf, %.svg, $(svgs))

tasks/fks/%.pdf: tasks/fks/%.svg
	@echo Converting $< to PDF:
	rsvg-convert --format pdf --keep-aspect-ratio --output temp/$*.pdf $<

clean:
	@echo Clean:
	rm -rf input
	find . -type f \( -name "*.log" -or -name "*.aux" -or -name "*.out" -or -name "*.*~" \) -delete	

distclean: clean
	@echo Dist clean:
	rm -rf output/

.PHONY: tasks solutions tasks.pdf solutions.pdf	
