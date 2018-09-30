MAKEFLAGS += --no-builtin-rules

.SECONDEXPANSION:

input/naboj/%/build-language:
	@echo -e '$(c_action)Building language for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/naboj/build-language.py 'source/naboj/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)' #FIX THIS

input/naboj/%/build-venue:
	@echo -e '$(c_action)Building venue for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/naboj/build-venue.py 'source/naboj/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/naboj/%/tearoff.tex: \
    input/naboj/$$*/build-venue \
	modules/naboj/templates/tearoff.tex \
    $$(subst $$(cdir),,$$(abspath source/naboj/$$*/meta.yaml)) ;

input/naboj/%/format.tex: \
    input/naboj/$$*/build-language \
	modules/naboj/format.tex \
	$$(subst $$(cdir),,$$(abspath input/naboj/$$*/../../../copy-static)) \
    $$(subst $$(cdir),,$$(abspath source/naboj/$$*/../meta.yaml)) ;

input/naboj/%/copy-static:
	@mkdir -p $(dir $@)static/
	cp -r source/naboj/$*/static/ input/naboj/$*/

input/naboj/%/booklet.tex input/naboj/%/answers.tex input/naboj/%/answers-mod5.tex input/naboj/%/cover.tex: \
    input/naboj/$$*/build-language \
	modules/naboj/templates/$$(notdir $@) \
    $$(subst $$(cdir),,$$(abspath source/naboj/$$*/../meta.yaml)) ;

input/naboj/%/intro.tex: \
    input/naboj/$$*/build-language \
	source/naboj/%/intro.tex ;

input/naboj/%/constants.tex: \
    input/naboj/$$*/build-language \
	modules/naboj/templates/constants.tex \
	source/naboj/%/constants-table.tex ;

input/naboj/%/instructions-text.tex: \
    input/naboj/$$*/build-language \
	source/naboj/%/instructions-text.tex ;

input/naboj/%/instructions.tex: \
    input/naboj/$$*/build-language \
	modules/naboj/templates/instructions.tex \
	source/naboj/%/instructions-text.tex ;

input/naboj/%/pdf-prerequisites: \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.jpg)) \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.png)) \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.pdf)) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/*/*.svg))) \
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/*/*.gp))) \
	$$(wildcard source/naboj/$$*/*/meta.yaml) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../meta.yaml)) ;

input/naboj/%/barcodes.txt: \
    $$(subst $$(cdir),,$$(abspath source/naboj/$$*/meta.yaml))
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/naboj/build-venue.py 'source/naboj/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/naboj/%/barcodes.pdf: \
	input/naboj/%/barcodes.txt
	@echo -e '$(c_action)Creating barcode PDF file $(c_filename)$@$(c_action):$(c_default)'
	barcode -e "128" -i $< -g "120x30" -p "120x30mm" -n -o $(subst .txt,.ps,$<)
	ps2pdf $(subst .txt,.ps,$<) $@.big
	pdfcrop $@.big $@

output/naboj/%/booklet.pdf: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/problem.md))) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/solution.md))) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/answer.md))) \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/format.tex \
	input/naboj/%/intro.tex \
	input/naboj/%/booklet.tex 
	mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): primary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=output/naboj/$*/booklet -halt-on-error -interaction=nonstopmode input/naboj/$*/booklet.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): secondary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=output/naboj/$*/booklet -halt-on-error -interaction=nonstopmode input/naboj/$*/booklet.tex

output/naboj/%/booklet-print.pdf: \
	output/naboj/%/booklet.pdf
	pdfbook --short-edge --quiet --outfile $@ $<

output/naboj/%/cover-print.pdf: \
	output/naboj/%/cover.pdf
	pdfnup --quiet --nup 2x1 $< --outfile $@

output/naboj/%/answers.pdf: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/answer.md))) \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/answers.tex 
	mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): primary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/answers.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): secondary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/answers.tex

output/naboj/%/answers-mod5.pdf: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/answer.md))) \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/answers-mod5.tex 
	mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): primary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/answers-mod5.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): secondary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/answers-mod5.tex

output/naboj/%/tearoff.pdf: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard $$(subst $(cdir),,$$(abspath source/naboj/$$*/../../languages/*/*/problem.md))))) \
	$$(subst source/,input/,$$(subst $(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/*/*.jpg)))) \
	$$(subst source/,input/,$$(subst $(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/*/*.png)))) \
	$$(subst source/,input/,$$(subst $(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/*/*.pdf)))) \
	$$(subst source/,input/,$$(subst $(cdir),,$$(abspath $$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/../../languages/*/*/*.svg))))) \
	$$(subst source/,input/,$$(subst $(cdir),,$$(abspath $$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/../../languages/*/*/*.gp))))) \
	input/naboj/%/barcodes.pdf \
	input/naboj/%/tearoff.tex 
	mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): primary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/tearoff.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): secondary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/tearoff.tex

output/naboj/%/constants.pdf: \
	input/naboj/%/constants.tex \
	input/naboj/%/constants-table.tex \
	$$(wildcard modules/naboj/templates/i18n/*.yaml)
	mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): primary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/constants.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): secondary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/constants.tex

output/naboj/%/instructions.pdf: \
	input/naboj/%/instructions.tex \
	input/naboj/%/instructions-text.tex \
	$$(wildcard modules/naboj/templates/i18n/*.yaml)
	mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): primary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/instructions.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): secondary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/instructions.tex

output/naboj/%/cover.pdf: \
	input/naboj/%/cover.tex \
	$$(subst $$(cdir),,$$(abspath input/naboj/$$*/../../../copy-static))
	mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): primary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/cover.tex

output/naboj/%/all: \
	output/naboj/$$*/booklet-print.pdf \
	output/naboj/$$*/answers.pdf \
	output/naboj/$$*/answers-mod5.pdf \
	output/naboj/$$*/constants.pdf \
	output/naboj/$$*/cover-print.pdf \
	output/naboj/$$*/instructions.pdf ;

output/naboj/%/all: \
	output/naboj/$$*/tearoff.pdf ;

output/naboj/%/languages/all: \
	$$(foreach dir,$$(dir $$(subst source/,output/,$$(wildcard source/naboj/$$*/languages/*/meta.yaml))), $$(dir)all) ; 

output/naboj/%/venues/all: \
	$$(foreach dir,$$(dir $$(subst source/,input/,$$(wildcard source/naboj/$$*/venues/*/meta.yaml))), $$(dir)all) ; 
