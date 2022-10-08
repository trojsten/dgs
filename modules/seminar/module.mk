.SECONDEXPANSION:

input/seminar/%/copy-static:
	@mkdir -p $(dir $@).static/
	cp -r source/seminar/$*/.static/ input/seminar/$*/

input/seminar/%/intro.tex input/seminar/%/rules.tex: \
	modules/seminar/templates/$$(notdir $@)
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 ./modules/seminar/build/volume.py 'source/seminar/' 'source/seminar/$*/' \
		-c $(word 1,$(words)) -v $(word 2,$(words)) -o '$(dir $@)'

input/seminar/%/problems.tex input/seminar/%/solutions.tex input/seminar/%/solutions-full.tex input/seminar/%/instagram.tex: \
	modules/seminar/templates/$$(notdir $@) \
	$$(wildcard source/seminar/$$*/*/meta.yaml) \
	source/seminar/$$*/meta.yaml
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 ./modules/seminar/build/round.py 'source/seminar/' 'modules/seminar/templates/' \
		-c $(word 1,$(words)) -v $(word 2,$(words)) -s $(word 3,$(words)) -r $(word 4,$(words)) -o '$(dir $@)'

input/seminar/%/semester.tex: \
	input/seminar/$$(word 1, $$(subst /, ,$$*))/$$(word 2, $$(subst /, ,$$*))/intro.tex \
	input/seminar/$$(word 1, $$(subst /, ,$$*))/$$(word 2, $$(subst /, ,$$*))/rules.tex \
	$$(wildcard source/seminar/$$*/*/*/problem.md) \
	$$(wildcard source/seminar/$$*/*/*/meta.yaml) \
	$$(wildcard source/seminar/$$*/*/meta.yaml) \
	source/seminar/$$*/meta.yaml
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 ./modules/seminar/build/semester.py 'source/seminar/' 'modules/seminar/templates/' -c $(word 1,$(words)) -v $(word 2,$(words)) -s $(word 3,$(words)) -o '$(dir $@)'

input/seminar/%/invite.tex: \
	modules/seminar/templates/$$(notdir $@) \
	source/seminar/$$*/meta.yaml
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/seminar/build/invite.py 'source/seminar/' 'modules/seminar/templates/' -c $(word 1,$(words)) -v $(word 2,$(words)) -s $(word 3,$(words)) -o '$(dir $@)'

# competition/volume/semester/round
input/seminar/%/pdf-prerequisites: \
	$$(subst $$(cdir),,$$(abspath input/seminar/$$*/../../../copy-static)) \
	$$(subst source/,input/,$$(wildcard source/seminar/$$*/*/*.jpg)) \
	$$(subst source/,input/,$$(wildcard source/seminar/$$*/*/*.png)) \
	$$(subst source/,input/,$$(subst .svg,.pdf,$$(wildcard source/seminar/$$*/*/*.svg))) \
	$$(subst source/,input/,$$(subst .gp,.pdf,$$(wildcard source/seminar/$$*/*/*.gp))) \
	$$(wildcard source/seminar/$$*/*/meta.yaml) \
	source/seminar/$$*/meta.yaml ;

output/seminar/%/html-prerequisites: \
	$$(subst source/,output/,$$(wildcard source/seminar/$$*/*/*.jpg)) \
	$$(subst source/,output/,$$(wildcard source/seminar/$$*/*/*.png)) \
	$$(subst source/,output/,$$(subst .svg,.png,$$(wildcard source/seminar/$$*/*/*.svg))) \
	$$(subst source/,output/,$$(subst .gp,.png,$$(wildcard source/seminar/$$*/*/*.gp))) ;

output/seminar/%/problems.pdf: \
	modules/seminar/templates/problems.tex \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/problem.md))) \
	input/seminar/$$*/pdf-prerequisites \
	input/seminar/$$*/problems.tex
	$(call doubletex,seminar)

output/seminar/%/solutions.pdf: \
	modules/seminar/templates/solutions.tex \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/solution.md))) \
	input/seminar/$$*/pdf-prerequisites \
	input/seminar/$$*/solutions.tex
	$(call doubletex,seminar)

output/seminar/%/solutions-full.pdf: \
	modules/seminar/templates/solutions-full.tex \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/problem.md))) \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/solution.md))) \
	input/seminar/$$*/pdf-prerequisites \
	input/seminar/$$*/solutions-full.tex
	$(call doubletex,seminar)

output/seminar/%/instagram.pdf: \
	modules/seminar/templates/instagram.tex \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/problem.md))) \
	input/seminar/$$*/pdf-prerequisites \
	input/seminar/$$*/instagram.tex
	$(call doubletex,seminar)

output/seminar/%/semester.pdf: \
	modules/seminar/templates/semester.tex \
	$$(subst source/,input/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/*/problem.md))) \
	input/seminar/$$*/pdf-prerequisites \
	input/seminar/$$*/semester.tex
	$(call doubletex,seminar)

output/seminar/%/invite.pdf:\
	source/seminar/$$*/meta.yaml \
	input/seminar/$$*/invite.tex
	$(call doubletex,seminar)

output/seminar/%/semester-print.pdf: \
	output/seminar/$$*/semester.pdf
	@echo -e '$(c_action)Converting $(c_filename)$<$(c_action) to a short-edge booklet $(c_filename)$@$(c_action):$(c_default)'
	pdfbook --short-edge --quiet --outfile $@ $<

output/seminar/%/instagram: \
	output/seminar/$$*/instagram.pdf
	@echo -e '$(c_action)Splitting $(c_filename)$<$(c_action) to individual images$(c_action):$(c_default)'
	pdftoppm -png -r 150 -aa yes -aaVector yes $< $@

### Batch outputs

output/seminar/%/html-problems: \
	output/seminar/$$*/html-prerequisites \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/seminar/$$*/*/problem.md))) ;
	
output/seminar/%/html-solutions:\
	output/seminar/$$*/html-prerequisites \
	$$(subst source/,output/,$$(subst .md,.html,$$(wildcard source/seminar/$$*/*/solution.md))) ;

output/seminar/%/pdf: \
	output/seminar/$$*/problems.pdf \
	output/seminar/$$*/solutions.pdf ;

output/seminar/%/html: \
	output/seminar/$$*/html-problems \
	output/seminar/$$*/html-solutions ;

output/seminar/%/problems: \
	output/seminar/$$*/problems.pdf \
	output/seminar/$$*/html-problems ;

output/seminar/%/solutions: \
	output/seminar/$$*/solutions.pdf \
	output/seminar/$$*/html-solutions ;

output/seminar/%: \
	output/seminar/$$*/problems \
	output/seminar/$$*/solutions \
	output/seminar/$$*/instagram ;

.PHONY:

output/seminar/%/copy: \
	output/seminar/%/
	$(eval words := $(subst /, ,$*))
	python3 ./dgs-copy.py $(word 1,$(words)) $(word 2,$(words)) $(word 3,$(words)) $(word 4,$(words)) $(user)
