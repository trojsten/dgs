all:                hello output/booklet.pdf output/answers.pdf output/tearoff.pdf

version =           '1.00'
date =              '2016-09-13'

texs =				$(wildcard temp/**/*.tex)
tex-to-tex =		$(patsubst temp%, input%, $(texs))

svgs =              $(wildcard temp/**/*.svg)
svg-to-pdf =		$(patsubst %.svg, %.pdf, $(patsubst temp%, input%, $(svgs)))
svg-to-png =		$(patsubst %.svg, %.png, $(patsubst temp%, output%, $(svgs)))

pdfs =				$(wildcard temp/**/*.pdf)
copy-pdf =			$(patsubst temp%, input%, $(pdfs))

pngs =              $(wildcard temp/**/*.png)
copy-png =			$(patsubst temp%, input%, $(pngs))

jpgs =				$(wildcard temp/**/*.jpg)
copy-jpg =			$(patsubst temp%, input%, $(jpgs))

hello:
	@echo -e '\e[32mThis is DeGeŠ Makefile, version \e[95m$(version)\e[32m [\e[95m$(date)\e[32m]\e[0m'

input/%.tex: temp/%.tex
	@echo -e '\e[32mCopying TeX file \e[96m$<\e[0m'
	mkdir -p $(dir $@)
	./core/dgs-convert.py ${language} $< $@
	vlna -l -r -v KkSsVvZzOoUuAaIi $@

input/%.pdf: temp/%.svg
	@echo -e '\e[32mConverting SVG file \e[96m$<\e[32m to PDF:\e[0m'
	mkdir -p $(dir $@)
	rsvg-convert --format pdf --keep-aspect-ratio --output $@ $<
	pdfcrop $@ $@-crop
	mv $@-crop $@

input/%.pdf: temp/%.pdf
	@echo -e '\e[32mCopying PDF file \e[96m$<\e[32m:\e[0m'
	cp $< $@

input/%.png: temp/%.png
	@echo -e '\e[32mCopying PNG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

input/%.jpg: temp/%.jpg
	@echo -e '\e[32mCopying JPG image \e[96m$<\e[32m:\e[0m'
	cp $< $@

output/answers.pdf: ${tex-to-tex} ${svg-to-pdf} ${copy-png} ${copy-jpg}
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/answers.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/answers.tex

output/booklet.pdf: ${tex-to-tex} ${svg-to-pdf} ${copy-png} ${copy-jpg}
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: primary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/booklet.tex
	@echo -e '\e[32mCompiling XeLaTeX file \e[96m$@\e[32m: secondary run\e[0m'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode core/templates/booklet.tex

output/tearoff.pdf: ${tex-to-tex} ${svg-to-pdf} ${copy-png} ${copy-jpg}
    
clean:
	@echo -e '\e[32mClean:\e[0m'
	rm -rf input/
	find . -type f \( -name "*.log" -or -name "*.aux" -or -name "*~" -or -name "*.out" -or -name "*.swp" \) -delete 

distclean: clean
	@echo -e '\e[32mDist clean:\e[0m'
	rm -rf temp/
	rm -rf output/

