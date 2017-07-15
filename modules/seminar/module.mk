MAKEFLAGS += --no-builtin-rules

.SECONDEXPANSION:

input/seminar/%/problems.tex input/seminar/%/solutions.tex:\
	$$(wildcard source/seminar/$$*/*/meta.yaml)\
	source/seminar/$$*/meta.yaml
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	./modules/seminar/build.py 'source/seminar/' $(word 1,$(words)) $(word 2,$(words)) $(word 3,$(words)) $(word 4,$(words)) -o '$(dir $@)'

input/seminar/%/pdf-prerequisites: \
	$$(subst source/,input/,$$(wildcard source/seminar/$$*/*/*.jpg)) \
	$$(subst source/,input/,$$(wildcard source/seminar/$$*/*/*.png)) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/seminar/$$*/*/*.svg))) \
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/seminar/$$*/*/*.gp))) \
	$$(wildcard source/seminar/$$*/*/meta.yaml) \
	source/seminar/$$*/meta.yaml ;

output/seminar/%/html-prerequisites: \
	$$(subst source/,output/,$$(wildcard source/seminar/$$*/*/*.jpg)) \
	$$(subst source/,output/,$$(wildcard source/seminar/$$*/*/*.png)) \
	$$(subst source/,output/,$$(subst .svg,.png,$$(wildcard source/$$*/*/*.svg))) \
	$$(subst source/,output/,$$(subst .gp,.png,$$(wildcard source/$$*/*/*.gp))) ;

output/seminar/%/problems.pdf: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/problem.md))) \
	input/seminar/%/pdf-prerequisites \
	input/seminar/%/problems.tex
	@mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), primary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/seminar/$*/problems.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), secondary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/seminar/$*/problems.tex

output/seminar/%/solutions.pdf: \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/solution.md))) \
	input/seminar/%/pdf-prerequisites \
	input/seminar/%/solutions.tex
	@mkdir -p $(dir $@)
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), primary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/seminar/$*/solutions.tex
	@echo -e '$(c_action)Compiling XeLaTeX file $(c_filename)$@$(c_action), secondary run:$(c_default)'
	@texfot xelatex -file-line-error -jobname=$(subst .pdf,,$@) -halt-on-error -interaction=nonstopmode input/seminar/$*/solutions.tex

output/seminar/%/html-problems: \
	output/seminar/%/html-prerequisites \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/seminar/$$*/*/problem.md))) ;
	
output/seminar/%/html-solutions:\
	output/seminar/%/html-prerequisites \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/seminar/$$*/*/solution.md))) ;

output/seminar/%/pdf: output/seminar/%/problems.pdf output/seminar/%/solutions.pdf ;

output/seminar/%/html: output/seminar/%/html-problems output/seminar/%/html-solutions ;

output/seminar/%/problems: output/seminar/%/problems.pdf output/seminar/%/html-problems ;

output/seminar/%/solutions: output/seminar/%/solutions.pdf output/seminar/%/html-solutions ;

output/seminar/%/all: output/seminar/%/problems output/seminar/%/solutions ;
