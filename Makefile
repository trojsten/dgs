all: make-tasks

define makedirs
	mkdir -p output
	mkdir -p temp
endef

make-tasks:    
	$(makedirs)
	xelatex -jobname=output/tasks -halt-on-error tasks.tex
	evince output/tasks.pdf &

make-solutions:
	xelatex -jobname=output/solutions -halt-on-error solutions.tex
	evince output/solutions.pdf &

svgs = $(wildcard tasks/fks/*.svg)
svg-to-pdf: $(patsubst %.pdf, %.svg, $(svgs))

tasks/fks/%.pdf: tasks/fks/%.svg
	@echo Converting $< to PDF:
	rsvg-convert --format pdf --keep-aspect-ratio --output temp/$*.pdf $<

clean:
	@echo Clean:
	rm -rf input
	find . -type f \( -name "*.log" -or -name "*.aux" -or -name "*.out" -or -name "*.*~" \) -delete	

#	rm -rf output
