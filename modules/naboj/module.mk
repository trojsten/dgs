MAKEFLAGS += --no-builtin-rules

.SECONDEXPANSION:

# Build scripts for language and venue prerequisites
# % <competition>/<volume>/<language>
input/naboj/%/build-language: \
	$$(subst $$(cdir),,$$(abspath input/naboj/$$*/../../../copy-static)) \
	source/naboj/$$*/meta.yaml \
	modules/naboj/templates/constants.tex
	@echo -e '$(c_action)Building language for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/naboj/build/language.py 'source/naboj/' 'modules/naboj/' -c $(word 1,$(words)) -v $(word 2,$(words)) -l $(word 4,$(words)) -o '$(dir $@)'

# % <competition>/<volume>/<venue>
input/naboj/%/build-venue: \
    $$(subst $$(cdir),,$$(abspath source/naboj/$$*/meta.yaml)) \
	$$(subst $$(cdir),,$$(abspath input/naboj/$$*/../../../copy-static)) \
	modules/naboj/templates/tearoff.tex
	@echo -e '$(c_action)Building venue for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/naboj/build/venue.py 'source/naboj/' 'modules/naboj/' -c $(word 1,$(words)) -v $(word 2,$(words)) -p $(word 4,$(words)) -o '$(dir $@)'

################################### input ####################################
# % <competition>/<volume>/<venue>
input/naboj/%/tearoff.tex: \
	modules/naboj/templates/$$(notdir $@) \
    input/naboj/$$*/build-venue ;

input/naboj/%/envelope.tex: \
	modules/naboj/templates/$$(notdir $@) \
    input/naboj/$$*/build-venue ;

input/naboj/%/format.tex: \
    input/naboj/$$*/build-language \
	modules/naboj/format.tex \
	$$(subst $$(cdir),,$$(abspath input/naboj/$$*/../../../copy-static)) \
    $$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) ;

input/naboj/%/booklet.tex input/naboj/%/answers.tex input/naboj/%/answers-mod5.tex input/naboj/%/cover.tex: \
	modules/naboj/templates/$$(notdir $$@) \
    input/naboj/$$*/build-language \
    $$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) ;

input/naboj/%/intro.tex: \
    input/naboj/$$*/build-language \
	source/naboj/%/intro.tex ;

input/naboj/%/constants.tex: \
    input/naboj/$$*/build-language \
	source/naboj/%/constants-table.tex ;

input/naboj/%/instructions-text.tex: \
    input/naboj/$$*/build-language \
	source/naboj/%/instructions-text.tex ;

input/naboj/%/instructions.tex: \
	modules/naboj/templates/$$(notdir $$@) \
    input/naboj/$$*/build-language \
	source/naboj/%/instructions-text.tex ;

input/naboj/%/pdf-prerequisites: \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.jpg)) \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.png)) \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.pdf)) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/*/*.svg))) \
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/*/*.gp))) \
	$$(wildcard source/naboj/$$*/*/meta.yaml) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) ;

output/naboj/%/booklet.pdf: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/problem.md))) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/solution.md))) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/answer.md))) \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/format.tex \
	input/naboj/%/intro.tex \
	input/naboj/%/booklet.tex 
	$(call doubletex,naboj)

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
	$(call doubletex,naboj)

output/naboj/%/answers-mod5.pdf: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/answer.md))) \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/answers-mod5.tex 
	$(call doubletex,naboj)

output/naboj/%/constants.pdf: \
	input/naboj/%/constants.tex \
	input/naboj/%/constants-table.tex \
	$$(wildcard modules/naboj/templates/i18n/*.yaml)
	$(call doubletex,naboj)

output/naboj/%/instructions.pdf: \
	input/naboj/%/instructions.tex \
	input/naboj/%/instructions-text.tex \
	$$(wildcard modules/naboj/templates/i18n/*.yaml)
	$(call doubletex,naboj)

output/naboj/%/cover.pdf: \
	input/naboj/%/cover.tex
	$(call doubletex,naboj)

########################## venue ################################

# Barcodes in text format
input/naboj/%/barcodes.txt: \
    $$(subst $$(cdir),,$$(abspath source/naboj/$$*/meta.yaml))
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/naboj/build-venue.py 'source/naboj/' -c $(word 1,$(words)) -v $(word 2,$(words)) -p $(word 4,$(words)) -o '$(dir $@)'

# Barcodes text -> PDF, one per page
input/naboj/%/barcodes.pdf: \
	input/naboj/%/barcodes.txt
	@echo -e '$(c_action)Creating barcode PDF file $(c_filename)$@$(c_action):$(c_default)'
	barcode -e "128" -i $< -g "120x30" -p "120x30mm" -n -o $(subst .txt,.ps,$<)
	ps2pdf $(subst .txt,.ps,$<) $@.big
	pdfcrop $@.big $@

# Tearoffs, three problems per page, aligned for cutting
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

output/naboj/%/envelope.pdf: \
	input/naboj/%/envelope.tex
	mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): primary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/envelope.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action): secondary run$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/naboj/$*/envelope.tex


# All targets for <language>
output/naboj/%/all: \
	output/naboj/$$*/booklet-print.pdf \
	output/naboj/$$*/answers.pdf \
	output/naboj/$$*/answers-mod5.pdf \
	output/naboj/$$*/constants.pdf \
	output/naboj/$$*/cover-print.pdf \
	output/naboj/$$*/instructions.pdf ;

# All targets for <venue>
output/naboj/%/all: \
	output/naboj/$$*/tearoff.pdf \
    output/naboj/$$*/envelope.pdf ;

# All targets for all languages
output/naboj/%/languages/all: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/languages/*/)), $$(dir)all) ; 

# All targets for all venues
output/naboj/%/venues/all: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/venues/*/)), $$(dir)all) ; 
