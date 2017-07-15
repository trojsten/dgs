MAKEFLAGS += --no-builtin-rules

.SUFFIXES:
	
module = seminar

.SECONDEXPANSION:

input/$(module)/%/problems.tex:\
	$$(wildcard source/$(module)/$$*/*/meta.yaml)\
	source/$(module)/$$*/meta.yaml
	$(eval words := $(subst /, ,$*))
	mkdir -p $(dir $@)
	./modules/$(module)/build.py 'source/$(module)/' $(word 1,$(words)) $(word 2,$(words)) $(word 3,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/$(module)/%/solutions.tex:\
	$$(wildcard source/$(module)/$$*/*/meta.yaml)\
	source/$(module)/$$*/meta.yaml
	$(eval words := $(subst /, ,$*))	
	mkdir -p $(dir $@)
	./modules/$(module)/build.py 'source/$(module)/' $(word 1,$(words)) $(word 2,$(words)) $(word 3,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/$(module)/%/pdf-prerequisites: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/$(module)/$$*/*/problem.md))) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/$(module)/$$*/*/*.svg))) \
	$$(subst source/,input/,$$(wildcard source/$(module)/$$*/*/*.jpg)) \
	$$(subst source/,input/,$$(wildcard source/$(module)/$$*/*/*.png)) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/$(module)/$$*/*/*.svg))) \
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/$(module)/$$*/*/*.gp))) \
	$$(wildcard source/$(module)/$$*/*/meta.yaml) \
	source/$(module)/$$*/meta.yaml ;

output/$(module)/%/copy-images: \
	$$(subst source/,output/,$$(wildcard source/$(module)/$$*/*/*.jpg)) \
	$$(subst source/,output/,$$(wildcard source/$(module)/$$*/*/*.png)) ;

output/$(module)/%/problems.pdf: \
	input/$(module)/%/pdf-prerequisites \
	output/$(module)/%/copy-images \
	input/$(module)/%/problems.tex
	mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), primary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/$(module)/$*/problems.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), secondary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/$(module)/$*/problems.tex

output/$(module)/%/solutions.pdf: \
	input/$(module)/%/pdf-prerequisites \
	output/$(module)/%/copy-images \
	input/$(module)/%/solutions.tex
	mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), primary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/$(module)/$*/solutions.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), secondary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/$(module)/$*/solutions.tex

output/$(module)/%/html-problems: \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/$$*/*/problem.md))) \
	$$(subst source/,output/,$$(subst .svg,.png,$$(wildcard source/$$*/*/*.svg))) \
	$$(subst source/,output/,$$(subst .png,.png,$$(wildcard source/$$*/*/*.png))) \
	$$(subst source/,output/,$$(subst .gp,.png,$$(wildcard source/$$*/*/*.gp))) ;

output/$(module)/%/html-solutions:\
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/$$*/*/solution.md))) \
	$$(subst source/,output/,$$(subst .svg,.png,$$(wildcard source/$$*/*/*.svg))) \
	$$(subst source/,output/,$$(subst .png,.png,$$(wildcard source/$$*/*/*.png))) \
	$$(subst source/,output/,$$(subst .gp,.png,$$(wildcard source/$$*/*/*.gp))) ;

output/$(module)/%/pdf: output/$(module)/%/problems.pdf output/$(module)/%/solutions.pdf ;

output/$(module)/%/html: output/$(module)/%/html-problems output/$(module)/%/html-solutions ;

output/$(module)/%/problems: output/$(module)/%/problems.pdf output/$(module)/%/html-problems ;

output/$(module)/%/solutions: output/$(module)/%/solutions.pdf output/$(module)/%/html-solutions ;

output/$(module)/%/all: output/$(module)/%/problems output/$(module)/%/solutions ;
