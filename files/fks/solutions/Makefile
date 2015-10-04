deps = ../../include/include ../zadania/zadania
images := $(patsubst %.svg,%.eps,$(wildcard *.svg))
priklady := $(patsubst %.tex,%.dvi,$(wildcard priklad*.tex))

all: vzoraky
vzoraky: vzoraky-web.pdf
		touch vzoraky
vzoraky-web: vzoraky

cleanall: clean-all
clean-all: clean
	rm -f *.ps *.pdf *.html
	rm vzoraky
clean:
	rm -f *.aux *.log *.dvi

../../include/include: FORCE
		$(MAKE) -C ../../include/ include
../zadania/zadania: FORCE
		$(MAKE) -C ../zadania zadania

$(images): %.eps: %.svg
#		svg2eps $<

$(priklady): priklad%.dvi: priklad%.tex $(images) $(wildcard *.eps) $(deps)
		echo $<
		vlna -l -r $<
		echo '\import{.}{' $< '}' > vzorak.tex
		cslatex preview.tex
		cslatex preview.tex
		cslatex preview.tex
		mv preview.dvi $@

priklad%.pdf: priklad%.dvi
		dvipdf $<

priklad%.tex.html: priklad%.tex
		text-vimcolor --filetype tex --format html $< > $@

vzoraky-web.dvi: vzoraky-web.tex vzoraky.tex $(priklady)
		vlna -l -r vzoraky-web.tex vzoraky.tex
		cslatex vzoraky-web.tex
		cslatex vzoraky-web.tex
		cslatex vzoraky-web.tex

vzoraky-web.pdf: %.pdf: %.dvi
		dvipdf $<

.PHONY: clean cleanall clean-all all
FORCE:
