.SECONDEXPANSION:

# Build scripts for language and venue prerequisites

# Shorthand for all i18n YAML definition files
source/naboj/%/i18n: \
	$$(wildcard source/naboj/$$*/.static/i18n/*.yaml) ;

# % <competition>/<volume>/languages/<language>
input/naboj/%/build-language: \
	$$(subst $$(cdir),,$$(abspath input/naboj/$$*/../../../copy-static)) \
	source/naboj/$$*/meta.yaml \
	source/naboj/$$(word 1,$$(subst /, ,$$*))/.static/i18n/$$(word 4,$$(subst /, ,$$*)).yaml ;
	@echo -e '$(c_action)Building language for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/naboj/build/language.py 'source/naboj/' 'modules/naboj/templates/' -c $(word 1,$(words)) -v $(word 2,$(words)) -l $(word 4,$(words)) -o '$(dir $@)'


# % <competition>/<volume>/<venue>
input/naboj/%/build-venue: \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/meta.yaml)) \
	$$(subst $$(cdir),,$$(abspath input/naboj/$$*/../../../copy-static)) \
	source/naboj/$$*/../../../i18n ;
	@echo -e '$(c_action)Building venue for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/naboj/build/venue.py 'source/naboj/' 'modules/naboj/templates/' -c $(word 1,$(words)) -v $(word 2,$(words)) -p $(word 4,$(words)) -o '$(dir $@)'

### Input files ###################################################################################

# % <competition>/<volume>/venues/<venue>
input/naboj/%/tearoff.tex: \
	modules/naboj/templates/base.tex \
	modules/naboj/templates/base-languages.tex \
	modules/naboj/templates/$$(notdir $$@) \
	modules/naboj/templates/tearoff-problem.tex \
	modules/naboj/templates/tearoff-bottom.tex \
	input/naboj/$$*/build-venue ;

# % <competition>/<volume>/venues/<venue>
input/naboj/%/envelope.tex: \
	modules/naboj/templates/$$(notdir $$@) \
	input/naboj/$$*/build-venue ;

# % <competition>/<volume>/languages/<language>
input/naboj/%/online.tex: \
	modules/naboj/templates/base.tex \
	modules/naboj/templates/base-languages.tex \
	modules/naboj/templates/$$(notdir $$@) \
    input/naboj/$$*/build-language ;

# Language-specific documents: booklet, answer sheet, answer sheet for evaluators, booklet cover
# % <competition>/<volume>/languages/<language>
input/naboj/%/booklet.tex input/naboj/%/answers.tex input/naboj/%/answers-mod5.tex input/naboj/%/cover.tex: \
	modules/naboj/templates/base.tex \
	modules/naboj/templates/base-languages.tex \
	modules/naboj/templates/$$(notdir $$@) \
	input/naboj/$$*/build-language \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) ;

# Introduction page for booklet
# % <competition>/<volume>/languages/<language>
input/naboj/%/intro.tex: \
	input/naboj/$$*/build-language \
	source/naboj/$$*/_extras/$$(notdir $$@) ;

# Constants sheet
# % <competition>/<volume>/languages/<language>
input/naboj/%/constants.tex: \
	modules/naboj/templates/constants.tex \
	input/naboj/$$*/build-language ;

# Instructions to be put on the table before the competition (content)
# % <competition>/<volume>/languages/<language>
input/naboj/%/instructions-inner.tex: \
	source/naboj/$$*/_extras/instructions-inner.tex \
	input/naboj/$$*/build-language ;

# Instructions to be put on the table before the competition (full document)
# % <competition>/<volume>/languages/<language>
input/naboj/%/instructions.tex: \
	modules/naboj/templates/$$(notdir $$@) \
	input/naboj/$$*/build-language ;

# Instructions before the online competition (content)
input/naboj/%/instructions-online-inner.tex: \
	source/naboj/$$*/_extras/instructions-online-inner.md
	@echo -e '$(c_action)[pandoc] Converting Markdown file $(c_filename)$<$(c_action) to TeX file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	python3 core/pandoc-convert.py latex sk $< $@ || exit 1;

# Instructions before the online competition (full document)
# % <competition>/<volume>/languages/<language>
input/naboj/%/instructions-online.tex: \
	modules/naboj/templates/$$(notdir $$@) \
	input/naboj/$$*/build-language ;

# PDF prerequisites (pictures, graphs, meta files)
# % <competition>/<volume>/languages/<language>
input/naboj/%/pdf-prerequisites: \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.jpg)) \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.png)) \
	$$(subst source/,input/,$$(wildcard source/naboj/$$*/*/*.pdf)) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/*/*.svg))) \
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/*/*.gp))) \
	$$(wildcard source/naboj/$$*/*/meta.yaml) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) ;

# All problems
input/naboj/%/problems: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/problem.md))) ;

input/naboj/%/solutions: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/solution.md))) ;

input/naboj/%/answers: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/answer.md))) ;

### Venues ######################################

# Barcodes in text format
input/naboj/%/barcodes.txt: \
	input/naboj/$$*/build-venue ;

# Barcodes text -> PDF, one per page
input/naboj/%/barcodes.pdf: \
	input/naboj/%/barcodes.txt
	@echo -e '$(c_action)Creating barcode PDF file $(c_filename)$@$(c_action):$(c_default)'
	barcode -e "128" -i $< -g "120x30" -p "120x30mm" -n -o $(subst .txt,.ps,$<)
	ps2pdf $(subst .txt,.ps,$<) $@.big
	pdfcrop $@.big $@



### Output files ##################################################################################
### Languages ###################################

# Full booklet
# % <competition>/<volume>/languages/<language>
output/naboj/%/booklet.pdf: \
	input/naboj/%/problems \
	input/naboj/%/solutions \
	input/naboj/%/answers \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/intro.tex \
	input/naboj/%/booklet.tex
	$(call doubletex,naboj)

# Full booklet folded for printing
# % <competition>/<volume>/languages/<language>
output/naboj/%/booklet-print.pdf: \
	output/naboj/%/booklet.pdf
	pdfbook --short-edge --quiet --outfile $@ $<

# "Virtual tearoffs" for online version, one problem per page
# % <competition>/<volume>/venues/<venue>
output/naboj/%/online.pdf: \
	input/naboj/%/problems \
	input/naboj/%/solutions \
	input/naboj/%/answers \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/online.tex
	$(call doubletex,naboj)
	pdftk $@ burst output $(dir $@)/%02d.pdf

output/naboj/%/html: \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/naboj/$$*/*/problem.md))) ;

output/naboj/%/cover-print.pdf: \
	output/naboj/%/cover.pdf
	pdfnup --quiet --nup 2x1 $< --outfile $@

output/naboj/%/answers.pdf: \
	input/naboj/%/answers \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/answers.tex
	$(call doubletex,naboj)

output/naboj/%/answers-mod5.pdf: \
	input/naboj/%/answers \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/answers-mod5.tex
	$(call doubletex,naboj)

output/naboj/%/constants.pdf: \
	input/naboj/%/constants.tex \
	source/naboj/%/i18n
	$(call doubletex,naboj)

output/naboj/%/instructions.pdf: \
	input/naboj/%/instructions.tex \
	input/naboj/%/instructions-inner.tex \
	source/naboj/%/i18n
	$(call doubletex,naboj)

output/naboj/%/instructions-online.pdf: \
	input/naboj/%/pdf-prerequisites \
	input/naboj/%/instructions-online.tex \
	input/naboj/%/instructions-online-inner.tex \
	source/naboj/%/i18n
	$(call doubletex,naboj)

output/naboj/%/cover.pdf: \
	input/naboj/%/cover.tex
	$(call doubletex,naboj)

# All targets for <language>
output/naboj/%: \
	output/naboj/$$*/booklet-print.pdf \
	output/naboj/$$*/answers.pdf \
	output/naboj/$$*/answers-mod5.pdf \
	output/naboj/$$*/constants.pdf \
	output/naboj/$$*/cover-print.pdf \
	output/naboj/$$*/instructions.pdf \
#	output/naboj/$$*/instructions-online.pdf \
#	output/naboj/$$*/online.pdf ;

# All targets for all languages
output/naboj/%/languages: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/languages/*)), $$(dir)) ;




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
	$(call doubletex,naboj)

# Envelope cover
output/naboj/%/envelope.pdf: \
	input/naboj/%/envelope.tex
	$(call doubletex,naboj)

# All targets for all venues
output/naboj/%/venues: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/venues/*/)), $$(dir)) ;
