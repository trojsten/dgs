all: make-tasks

define makedirs
	mkdir -p output
	mkdir -p temp
endef

make-tasks:    
	$(makedirs)
	xelatex -jobname=output/tasks -halt-on-error tasks.tex
	evince output/tasks.pdf &

svgs = $(wildcard tasks/fks/*.svg)
svg-to-pdf: $(patsubst %.pdf, %.svg, $(svgs))

tasks/fks/%.pdf: tasks/fks/%.svg
	@echo Converting $< to PDF:
	rsvg-convert --format pdf --keep-aspect-ratio --output temp/$*.pdf $<

clean:
	@echo Clean:
	rm -rf input
#	rm -rf output
