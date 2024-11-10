.SECONDEXPANSION:

# Build scripts for language and venue prerequisites

# Shorthand for all i18n YAML definition files
source/naboj/%/i18n: \
	$$(wildcard source/naboj/$$*/.static/i18n/*.yaml) ;

# DeGeŠ convert Markdown file to TeX (for XeLaTeX)
# % <competition>/<volume>/problems/<language>/<problem>
# Overrides global convertor!

build/naboj/%/answer.tex: \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../$$(subst .tex,.md,$$(notdir $$@))))
	$(eval language := $(word 5,$(subst /, ,$*)))
	$(call pandoctex,$(language))

build/naboj/%/answer-also.tex: \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../$$(subst .tex,.md,$$(notdir $$@))))
	$(eval language := $(word 5,$(subst /, ,$*)))
	$(call pandoctex,$(language))

build/naboj/%/answer-interval.tex: \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../$$(subst .tex,.md,$$(notdir $$@))))
	$(eval language := $(word 5,$(subst /, ,$*)))
	$(call pandoctex,$(language))

build/naboj/%.tex: \
	source/naboj/%.md
	$(eval language := $(word 5,$(subst /, ,$*)))
	$(call pandoctex,$(language))

define truepath
	$$(subst $$(cdir),,$(1))
endef

# % <competition>/<volume>/languages/<language>

# prepare_arguments(target)
# target = language | venue
define prepare_arguments
	@mkdir -p $(dir $@)
	@echo -e '$(c_action)Building $(1) for $(c_filename)$*$(c_action):$(c_default)'
	$(eval words := $(subst /, ,$*))
endef

build/naboj/%/build-language: \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../../copy-static)) \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../../.static/logo/logo.pdf)) \
	source/naboj/$$*/meta.yaml \
	source/naboj/$$(word 1,$$(subst /, ,$$*))/.static/i18n/$$(word 4,$$(subst /, ,$$*)).yaml
	$(call prepare_arguments,language)
	python -m modules.naboj.builder.language 'source/naboj/' 'modules/naboj/templates/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

# % <competition>/<volume>/venues/<venue>
build/naboj/%/build-venue: \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/meta.yaml)) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../../meta.yaml)) \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../../copy-static)) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../../i18n))
	$(call prepare_arguments,venue)
	python -m modules.naboj.builder.venue 'source/naboj/' 'modules/naboj/templates/' $(word 1,$(words)) $(word 2,$(words)) $(word 4,$(words)) -o '$(dir $@)'

### Input files ###################################################################################

# % <competition>/<volume>/venues/<venue>
build/naboj/%/envelopes.tex: \
	modules/naboj/templates/envelopes.jtt \
	build/naboj/$$*/build-venue ;

# Language-specific documents: booklet, answer sheet, answer sheet for evaluators, booklet cover
# % <competition>/<volume>/languages/<language>
build/naboj/%/online.tex: \
	modules/naboj/templates/base.jtt \
	modules/naboj/templates/base-booklet.jtt \
	modules/naboj/templates/online.jtt \
    build/naboj/$$*/build-language ;

# % <competition>/<volume>/languages/<language>
build/naboj/%/tearoff.tex: \
	modules/naboj/templates/base.jtt \
	modules/naboj/templates/base-tearoff.jtt \
	modules/naboj/templates/tearoff.jtt \
	modules/naboj/templates/tearoff/problem.jtt \
	modules/naboj/templates/tearoff/bottom.jtt \
	build/naboj/$$*/build-language ;

# % <competition>/<volume>/languages/<language>
build/naboj/%/booklet.tex build/naboj/%/answers.tex build/naboj/%/cover.tex: \
	modules/naboj/templates/base.jtt \
	modules/naboj/templates/footer.jtt \
	modules/naboj/templates/colophon.jtt \
	modules/naboj/templates/base-booklet.jtt \
	modules/naboj/templates/answer.jtt \
	modules/naboj/templates/$$(subst .tex,.jtt,$$(notdir $$@)) \
	build/naboj/$$*/build-language \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../../meta.yaml)) ;

# Introduction page for booklet
# % <competition>/<volume>/languages/<language>
build/naboj/%/intro.tex: \
	source/naboj/$$*/intro.jtt \
	build/naboj/$$*/build-language ;

# Constants sheet
# % <competition>/<volume>/languages/<language>
build/naboj/%/constants.tex: \
	modules/naboj/templates/constants.jtt \
	build/naboj/$$*/build-language ;

# Instructions to be put on the table before the competition (content)
# % <competition>/<volume>/venues/<venue>
build/naboj/%/instructions-inner.tex: \
	source/naboj/$$*/$$(subst .tex,.jtt,$$(notdir $$@)) \
	build/naboj/$$*/build-language ;

build/naboj/%/evaluators.tex: \
	source/naboj/$$*/$$(subst .tex,.jtt,$$(notdir $$@)) \
	build/naboj/$$*/build-venue ;

# Instructions to be put on the table before the competition (full document)
# % <competition>/<volume>/venues/<venue>
build/naboj/%/instructions.tex: \
	modules/naboj/templates/$$(notdir $$@) \
	build/naboj/$$*/build-venue ;

# Instructions before the online competition (content)
build/naboj/%/instructions-online-inner.tex: \
	source/naboj/$$*/_extras/instructions-online-inner.md
	$(eval language := $(word 4,$(subst /, ,$*)))
	@echo -e '$(c_action)[pandoc] Converting Markdown file $(c_filename)$<$(c_action) to TeX file $(c_filename)$@$(c_action):$(c_default)'
	@mkdir -p $(dir $@)
	python core/pandoc-convert.py latex $(language) $< $@ || exit 1;

# Instructions before the online competition (full document)
# % <competition>/<volume>/languages/<language>
build/naboj/%/instructions-online.tex: \
	modules/naboj/templates/$$(notdir $$@) \
	build/naboj/$$*/build-language ;

# PDF prerequisites (pictures, graphs, meta files)
# % <competition>/<volume>
build/naboj/%/pdf-prerequisites: \
	core/latex/dgs.cls \
	$$(wildcard core/latex/*.tex) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*/*.png)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*.pdf)) \
	$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*/*.pdf)) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/problems/*/*.svg))) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/problems/*/*/*.svg))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/problems/*/*.gp))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/problems/*/*/*.gp))) \
	$$(wildcard source/naboj/$$*/meta.yaml) \
	$$(subst $$(cdir),,$$(abspath source/naboj/$$*/../meta.yaml)) \
	build/core/i18n ;

# All problems, solutions and answers for every language, and overall
# <competition>/<volume>
define RULE_TEMPLATE
build/naboj/%/problems/$(1): \
	$$$$(subst source/,build/,$$$$(subst .md,.tex,$$$$(wildcard source/naboj/$$$$*/problems/*/$(1)/problem.md))) ;

build/naboj/%/solutions/$(1): \
	$$$$(subst source/,build/,$$$$(subst .md,.tex,$$$$(wildcard source/naboj/$$$$*/problems/*/$(1)/solution.md))) ;

build/naboj/%/answers/$(1): \
	$$$$(addsuffix answer.tex,$$$$(subst source/,build/,$$$$(wildcard source/naboj/$$$$*/problems/*/$(1)/))) \
	$$$$(subst source/,build/,$$$$(subst .md,.tex,$$$$(wildcard source/naboj/$$$$*/problems/*/$(1)/answer-extra.md))) \
	$$$$(addsuffix $(1)/answer-also.tex,$$$$(subst source/,build/,$$$$(dir $$$$(wildcard source/naboj/$$$$*/problems/*/answer-also.md)))) \
	$$$$(addsuffix $(1)/answer-interval.tex,$$$$(subst source/,build/,$$$$(dir $$$$(wildcard source/naboj/$$$$*/problems/*/answer-interval.md)))) ;

build/naboj/%/$(1): \
	build/naboj/%/problems/$(1) \
	build/naboj/%/solutions/$(1) \
	build/naboj/%/answers/$(1) ;
endef
$(foreach language,$(SUPPORTED_LANGUAGES),$(eval $(call RULE_TEMPLATE,$(language))))

build/naboj/%/problems: \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/problems/*/*/problem.md))) ;

build/naboj/%/solutions: \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/problems/*/*/solution.md))) ;

build/naboj/%/answers: \
	$$(addsuffix answer.tex,$$(subst source/,build/,$$(wildcard source/naboj/$$*/problems/*/*/))) \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/naboj/$$*/problems/*/*/answer-extra.md))) \
	$$(addsuffix answer-also.tex,$$(subst source/,build/,$$(foreach int,$$(wildcard source/naboj/$$*/problems/*/answer-also.md),$$(wildcard $$(dir $$(int))*/)))) \
	$$(addsuffix answer-interval.tex,$$(subst source/,build/,$$(foreach int,$$(wildcard source/naboj/$$*/problems/*/answer-interval.md),$$(wildcard $$(dir $$(int))*/)))) ;

### Venues ######################################

# Answers-modulo
build/naboj/%/answers-modulo.tex: \
	modules/naboj/templates/answer.jtt \
	modules/naboj/templates/answers-modulo.jtt \
	build/naboj/$$*/build-venue ;

# Barcodes in text format
build/naboj/%/barcodes.tex: \
	build/naboj/$$*/build-venue ;

# Barcodes text -> PDF, one per page
build/naboj/%/barcodes.pdf: \
	build/naboj/%/barcodes.tex
	@echo -e '$(c_action)Creating barcode PDF file $(c_filename)$@$(c_action):$(c_default)'
	barcode -e "128" -i $< -g "120x30" -p "120x30mm" -n -o $(subst .tex,.ps,$<)
	ps2pdf $(subst .tex,.ps,$<) $@.big
	pdfcrop $@.big $@



### Output files ##################################################################################
### Languages ###################################

# Full booklet
# % <competition>/<volume>/languages/<language>
output/naboj/%/booklet.pdf: \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../$$(word 4,$$(subst /, ,$$*)))) \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../pdf-prerequisites)) \
	build/naboj/%/problems \
	build/naboj/%/solutions \
	build/naboj/%/answers \
	build/naboj/%/intro.tex \
	build/naboj/%/booklet.tex
	$(call double_xelatex,naboj)

# Full booklet folded for printing
# % <competition>/<volume>/languages/<language>
output/naboj/%/booklet-print.pdf: \
	output/naboj/%/booklet.pdf ;
	pdfbook2 --short-edge --paper a4paper --outer-margin=40 --inner-margin=40 --top-margin=30 --bottom-margin=30 $<
	mv output/naboj/$*/booklet-book.pdf $@

# "Virtual tearoffs" for online version, one problem per page
# % <competition>/<volume>/venues/<venue>
output/naboj/%/online.pdf: \
	build/naboj/%/problems \
	build/naboj/%/solutions \
	build/naboj/%/answers \
	build/naboj/%/pdf-prerequisites \
	build/naboj/%/online.tex
	$(call double_xelatex,naboj)
	pdftk $@ burst output $(dir $@)/%02d.pdf

# % <competition>/<volume>
output/naboj/%/languages/tearoffs.zip: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/languages/*)),$$(dir)/tearoff.pdf)
	$(foreach path,$^,ln -sf $(notdir $(path)) $(subst tearoff,$(word 6,$(subst /, ,$(path))),$(path));)
	zip --junk-paths $@ $(foreach path,$^,$(subst tearoff,$(word 6,$(subst /, ,$(path))),$(path)))

output/naboj/%/html: \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/naboj/$$*/*/problem.md))) \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/naboj/$$*/*/solution.md))) \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/naboj/$$*/*/answer.md))) ;

output/naboj/%/answers.pdf: \
	$$(subst $$(cdir),,$$(abspath build/naboj/%/../../answers/$$(word 4,$$(subst /, ,$$*)))) \
	$$(subst $$(cdir),,$$(abspath build/naboj/%/../../pdf-prerequisites)) \
	build/naboj/%/answers.tex
	$(call double_xelatex,naboj)

output/naboj/%/constants.pdf: \
	build/naboj/%/constants.tex \
	source/naboj/%/i18n
	$(call double_xelatex,naboj)

output/naboj/%/instructions-online.pdf: \
	build/naboj/%/pdf-prerequisites \
	build/naboj/%/instructions-online.tex \
	build/naboj/%/instructions-online-inner.tex \
	source/naboj/%/i18n
	$(call double_xelatex,naboj)

output/naboj/%/cover.pdf: \
	build/naboj/%/cover.tex
	$(call double_xelatex,naboj)

output/naboj/%/cover-print.pdf: \
	output/naboj/%/cover.pdf
	pdfjam --quiet --nup "2x1" --landscape --outfile $@ $<

# All targets for <language>
# <competition>/<volume>
output/naboj/%: \
	output/naboj/%/answers.pdf \
	output/naboj/%/constants.pdf \
	output/naboj/%/cover-print.pdf \
	output/naboj/%/booklet.pdf \
	output/naboj/%/booklet-print.pdf ;
#	output/naboj/$$*/instructions-online.pdf \
#	output/naboj/$$*/online.pdf ;

# <competition>/<volume>
output/naboj/%/booklets: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/languages/*)),$$(dir)/booklet.pdf) ;

# All targets for all languages
# <competition>/<volume>
output/naboj/%/languages: \
	$$(foreach dir,$$(subst source/,output/,$$(wildcard source/naboj/$$*/languages/*)),$$(dir)) \
	$$@/tearoffs.zip ;

# Tearoffs, three problems per page, aligned for cutting
# <competition>/<volume>/<venues>/<venue>
output/naboj/%/tearoff.pdf: \
	$$(subst source/,build/,$$(subst .md,.tex,$$(subst $$(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../problems/*/*/problem.md))))) \
	$$(subst $$(cdir),,$$(abspath build/naboj/$$*/../../pdf-prerequisites)) \
	build/naboj/%/tearoff.tex
	$(call double_xelatex,naboj)

# Envelope cover
output/naboj/%/envelopes.pdf: \
	build/naboj/%/envelopes.tex
	$(call double_xelatex,naboj)

output/naboj/%/instructions.pdf: \
	build/naboj/%/instructions.tex \
	$$(subst source/,build/,$$(wildcard $$(subst $(cdir),,$$(abspath source/naboj/$$*/../../languages/*/instructions-inner.tex)))) \
	source/naboj/%/i18n
	$(call double_xelatex,naboj)

# <competition>/<volume>/venues/<venue>
output/naboj/%/answers-modulo.pdf: \
	$$(subst source/,build/,$$(subst $(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/*/*.jpg)))) \
	$$(subst source/,build/,$$(subst $(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/*/*.png)))) \
	$$(subst source/,build/,$$(subst $(cdir),,$$(abspath $$(wildcard source/naboj/$$*/../../languages/*/*/*.pdf)))) \
	$$(subst source/,build/,$$(subst $(cdir),,$$(abspath $$(subst .svg,.pdf,$$(wildcard source/naboj/$$*/../../languages/*/*/*.svg))))) \
	$$(subst source/,build/,$$(subst $(cdir),,$$(abspath $$(subst .gp,.pdf,$$(wildcard source/naboj/$$*/../../languages/*/*/*.gp))))) \
	$$(subst $$(cdir),,$$(abspath build/naboj/%/../../answers)) \
	$$(subst $$(cdir),,$$(abspath build/naboj/%/../../pdf-prerequisites)) \
	build/naboj/%/answers-modulo.tex \
	build/naboj/%/evaluators.tex
	$(call double_xelatex,naboj)



# All targets for <venue>
# <competition>/<volume>/venues/<venue>
output/naboj/%: \
	output/naboj/%/instructions.pdf \
	output/naboj/%/answers-modulo.pdf \
	output/naboj/%/envelopes.pdf ;

# All targets for all venues
# <competition>/<volume>
output/naboj/%/venues:
#	$$(subst source/,output/,$$(wildcard source/naboj/$$*/venues/*)) ;
	@echo $(subst source/,output/,$(wildcard source/naboj/$*/venues/*)) ;

output/naboj/%/all: \
	output/naboj/%/languages \
	output/naboj/%/venues ;

output/naboj/%/copy: \
	output/naboj/%
	rsync -rzvhPL output/naboj/$*/ ago:/home/balaz/public_html/naboj/$(subst output/,,$*)
