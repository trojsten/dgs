.SECONDEXPANSION:

# Build scripts for language and venue prerequisites

# Shorthand for all i18n YAML definition files
source/naboj/%/i18n: \
	$$(wildcard source/naboj/$$*/.static/i18n/*.yaml) ;

# DeGeŠ convert Markdown file to TeX (for XeLaTeX)
# % <competition>/<volume>/languages/<language>/<problem>
build/naboj/%.tex: source/naboj/%.md
	$(eval language := $(word 4,$(subst /, ,$*)))
	$(call pandoctex,$(language))

# % <competition>/<volume>/languages/<language>

build/naboj/%/build-language: \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../../copy-static)) \
	build/naboj/$$*/../../../.static/logo/logo.pdf \
	source/naboj/$$*/meta.yaml \
	source/naboj/$$(word 1,$$(subst /, ,$$*))/.static/i18n/$$(word 4,$$(subst /, ,$$*)).yaml ;
	@echo -e '$(c_action)Building language for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/naboj/builder/language.py 'source/naboj/' 'modules/naboj/templates/' -c $(word 1,$(words)) -v $(word 2,$(words)) -l $(word 4,$(words)) -o '$(dir $@)'


# % <competition>/<volume>/<venue>
build/naboj/%/build-venue: \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/meta.yaml)) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../../copy-static)) \
	source/naboj/$$*/../../../i18n ;
	@echo -e '$(c_action)Building venue for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/naboj/builder/venue.py 'source/naboj/' 'modules/naboj/templates/' -c $(word 1,$(words)) -v $(word 2,$(words)) -p $(word 4,$(words)) -o '$(dir $@)'

### Input files ###################################################################################

# % <competition>/<volume>/venues/<venue>
build/naboj/%/tearoff.tex: \
	modules/naboj/templates/base.tex \
	modules/naboj/templates/base-languages.tex \
	modules/naboj/templates/$$(notdir $$@) \
	modules/naboj/templates/tearoff-problem.tex \
	modules/naboj/templates/tearoff-bottom.tex \
	build/naboj/$$*/build-venue ;

# % <competition>/<volume>/venues/<venue>
build/naboj/%/envelopes.tex: \
	modules/naboj/templates/$$(notdir $$@) \
	build/naboj/$$*/build-venue ;

# % <competition>/<volume>/languages/<language>
build/naboj/%/online.tex: \
	modules/naboj/templates/base.tex \
	modules/naboj/templates/base-languages.tex \
	modules/naboj/templates/$$(notdir $$@) \
    build/naboj/$$*/build-language ;

# Language-specific documents: booklet, answer sheet, answer sheet for evaluators, booklet cover
# % <competition>/<volume>/languages/<language>
build/naboj/%/booklet.tex build/naboj/%/answers.tex build/naboj/%/answers-modulo.tex build/naboj/%/cover.tex: \
	modules/naboj/templates/base.tex \
	modules/naboj/templates/base-languages.tex \
	modules/naboj/templates/$$(notdir $$@) \
	build/naboj/$$*/build-language \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) ;

# Introduction page for booklet
# % <competition>/<volume>/languages/<language>
build/naboj/%/intro.tex: \
	build/naboj/$$*/build-language \
	source/naboj/$$*/_extras/$$(notdir $$@) ;

# Constants sheet
# % <competition>/<volume>/languages/<language>
build/naboj/%/constants.tex: \
	modules/naboj/templates/constants.tex \
	build/naboj/$$*/build-language ;

# Instructions to be put on the table before the competition (content)
# % <competition>/<volume>/languages/<language>
build/naboj/%/instructions-inner.tex: \
	source/naboj/$$*/_extras/instructions-inner.tex \
	build/naboj/$$*/build-language ;

# Instructions to be put on the table before the competition (full document)
# % <competition>/<volume>/languages/<language>
build/naboj/%/instructions.tex: \
	modules/naboj/templates/$$(notdir $$@) \
	build/naboj/$$*/build-language ;

# Instructions before the online competition (content)
build/naboj/%/instructions-online-inner.tex: \
	source/naboj/$$*/_extras/instructions-online-inner.md
	$(eval language := $(word 4,$(subst /, ,$*)))
	@echo -e '$(c_action)[pandoc] Converting Markdown file $(c_filename)$<$(c_action) to TeX file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	python3 core/pandoc-convert.py latex $(language) $< $@ || exit 1;

# Instructions before the online competition (full document)
# % <competition>/<volume>/languages/<language>
build/naboj/%/instructions-online.tex: \
	modules/naboj/templates/$$(notdir $$@) \
	build/naboj/$$*/build-language ;

# PDF prerequisites (pictures, graphs, meta files)
# % <competition>/<volume>/languages/<language>
build/naboj/%/pdf-prerequisites: \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/*/*.pdf)) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/*/*.svg))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/*/*.gp))) \
	$$(wildcard source/naboj/$$*/*/meta.yaml) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) ;

# All problems
build/naboj/%/problems: \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/problem.md))) ;

build/naboj/%/solutions: \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/solution.md))) ;

build/naboj/%/answers: \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/*/answer.md))) ;

### Venues ######################################

# Barcodes in text format
build/naboj/%/barcodes.txt: \
	build/naboj/$$*/build-venue ;

# Barcodes text -> PDF, one per page
build/naboj/%/barcodes.pdf: \
	build/naboj/%/barcodes.txt
	@echo -e '$(c_action)Creating barcode PDF file $(c_filename)$@$(c_action):$(c_default)'
	barcode -e "128" -i $< -g "120x30" -p "120x30mm" -n -o $(subst .txt,.ps,$<)
	ps2pdf $(subst .txt,.ps,$<) $@.big
	pdfcrop $@.big $@



### Output files ##################################################################################
### Languages ###################################

# Full booklet
# % <competition>/<volume>/languages/<language>
output/naboj/%/booklet.pdf: \
	build/naboj/%/problems \
	build/naboj/%/solutions \
	build/naboj/%/answers \
	build/naboj/%/pdf-prerequisites \
	build/naboj/%/intro.tex \
	build/naboj/%/booklet.tex
	$(call doubletex,naboj)

# Full booklet folded for printing
# % <competition>/<volume>/languages/<language>
output/naboj/%/booklet-print.pdf: \
	output/naboj/%/booklet.pdf
	pdfbook --short-edge --quiet --outfile $@ $<

# "Virtual tearoffs" for online version, one problem per page
# % <competition>/<volume>/venues/<venue>
output/naboj/%/online.pdf: \
	build/naboj/%/problems \
	build/naboj/%/solutions \
	build/naboj/%/answers \
	build/naboj/%/pdf-prerequisites \
	build/naboj/%/online.tex
	$(call doubletex,naboj)
	pdftk $@ burst output $(dir $@)/%02d.pdf

output/naboj/%/html: \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/naboj/$$*/*/problem.md))) \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/naboj/$$*/*/solution.md))) \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/naboj/$$*/*/answer.md))) ;

output/naboj/%/cover-print.pdf: \
	output/naboj/%/cover.pdf
	pdfnup --quiet --nup 2x1 $< --outfile $@

output/naboj/%/answers.pdf: \
	build/naboj/%/answers \
	build/naboj/%/pdf-prerequisites \
	build/naboj/%/answers.tex
	$(call doubletex,naboj)

output/naboj/%/answers-modulo.pdf: \
	build/naboj/%/answers \
	build/naboj/%/pdf-prerequisites \
	build/naboj/%/answers-modulo.tex
	$(call doubletex,naboj)

output/naboj/%/constants.pdf: \
	build/naboj/%/constants.tex \
	source/naboj/%/i18n
	$(call doubletex,naboj)

output/naboj/%/instructions.pdf: \
	build/naboj/%/instructions.tex \
	build/naboj/%/instructions-inner.tex \
	source/naboj/%/i18n
	$(call doubletex,naboj)

output/naboj/%/instructions-online.pdf: \
	build/naboj/%/pdf-prerequisites \
	build/naboj/%/instructions-online.tex \
	build/naboj/%/instructions-online-inner.tex \
	source/naboj/%/i18n
	$(call doubletex,naboj)

output/naboj/%/cover.pdf: \
	build/naboj/%/cover.tex
	$(call doubletex,naboj)

# All targets for <language>
output/naboj/%: \
	output/naboj/%/answers.pdf \
	output/naboj/%/answers-modulo.pdf \
	output/naboj/%/constants.pdf \
	output/naboj/%/cover-print.pdf \
	output/naboj/%/booklet-print.pdf \
	output/naboj/%/instructions.pdf ;
#	output/naboj/$$*/instructions-online.pdf \
#	output/naboj/$$*/online.pdf ;

# competition/volume
output/naboj/%/booklets: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/languages/*)),$$(dir)/booklet.pdf);

# All targets for all languages
# competition/volume
output/naboj/%/languages: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/languages/*)),$$(dir)) ;




# Tearoffs, three problems per page, aligned for cutting
output/naboj/%/tearoff.pdf: \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard $$(subst $(cdir),,$$(abspath source/naboj/$$*/../../languages/*/*/problem.md))))) \
	$$(subst source/,build/,$$(subst $(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/*/*.jpg)))) \
	$$(subst source/,build/,$$(subst $(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/*/*.png)))) \
	$$(subst source/,build/,$$(subst $(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/*/*.pdf)))) \
	$$(subst source/,build/,$$(subst $(cdir),,$$(abspath $$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/../../languages/*/*/*.svg))))) \
	$$(subst source/,build/,$$(subst $(cdir),,$$(abspath $$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/../../languages/*/*/*.gp))))) \
	build/naboj/%/barcodes.pdf \
	build/naboj/%/tearoff.tex
	$(call doubletex,naboj)

# Envelope cover
output/naboj/%/envelopes.pdf: \
	build/naboj/%/envelopes.tex
	$(call doubletex,naboj)



# All targets for <venue>
# <competition>/<volume>/venues/<venue>
output/naboj/%: \
	output/naboj/%/tearoff.pdf \
	output/naboj/%/envelopes.pdf ;

# All targets for all venues
# <competition>/<volume>
output/naboj/%/venues: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/venues/*/)), $$(dir)) ;

output/naboj/%: \
	output/naboj/%/languages \
	output/naboj/%/venues ;

output/naboj/%/copy: \
	output/naboj/%
	rsync -rzvhPL output/naboj/$*/ fks:/home/sesquideus/public_html/naboj/$(subst output/,,$*)
