.SECONDEXPANSION:

build/seminar/%/copy-static:
	@mkdir -p $(dir $@).static/
	cp -r source/seminar/$*/.static/ build/seminar/$*/

build/seminar/%/intro.tex build/seminar/%/rules.tex: \
	modules/seminar/templates/$$(notdir $@)
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 ./modules/seminar/build/volume.py 'source/seminar/' 'source/seminar/$*/' \
		-c $(word 1,$(words)) -v $(word 2,$(words)) -o '$(dir $@)'

build/seminar/%/problems.tex build/seminar/%/solutions.tex build/seminar/%/solutions-full.tex build/seminar/%/instagram.tex: \
	modules/seminar/templates/$$(notdir $@) \
	$$(wildcard source/seminar/$$*/*/meta.yaml) \
	source/seminar/$$*/meta.yaml
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 ./modules/seminar/build/round.py 'source/seminar/' 'modules/seminar/templates/' \
		-c $(word 1,$(words)) -v $(word 2,$(words)) -s $(word 3,$(words)) -r $(word 4,$(words)) -o '$(dir $@)'

build/seminar/%/semester.tex: \
	build/seminar/$$(word 1, $$(subst /, ,$$*))/$$(word 2, $$(subst /, ,$$*))/intro.tex \
	build/seminar/$$(word 1, $$(subst /, ,$$*))/$$(word 2, $$(subst /, ,$$*))/rules.tex \
	$$(wildcard source/seminar/$$*/*/*/problem.md) \
	$$(wildcard source/seminar/$$*/*/*/meta.yaml) \
	$$(wildcard source/seminar/$$*/*/meta.yaml) \
	source/seminar/$$*/meta.yaml
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 ./modules/seminar/build/semester.py 'source/seminar/' 'modules/seminar/templates/' -c $(word 1,$(words)) -v $(word 2,$(words)) -s $(word 3,$(words)) -o '$(dir $@)'

build/seminar/%/invite.tex: \
	modules/seminar/templates/$$(notdir $@) \
	source/seminar/$$*/meta.yaml
	$(eval words := $(subst /, ,$*))
	@mkdir -p $(dir $@)
	python3 modules/seminar/build/invite.py 'source/seminar/' 'modules/seminar/templates/' -c $(word 1,$(words)) -v $(word 2,$(words)) -s $(word 3,$(words)) -o '$(dir $@)'

# competition/volume/semester/round
build/seminar/%/pdf-prerequisites: \
	$$(subst $$(cdir),,$$(abspath build/seminar/$$*/../../../copy-static)) \
	$$(subst source/,build/,$$(wildcard source/seminar/$$*/*/*.pdf)) \
	$$(subst source/,build/,$$(wildcard source/seminar/$$*/*/*.jpg)) \
	$$(subst source/,build/,$$(wildcard source/seminar/$$*/*/*.png)) \
	$$(subst source/,build/,$$(subst .svg,.pdf,$$(wildcard source/seminar/$$*/*/*.svg))) \
	$$(subst source/,build/,$$(subst .gp,.pdf,$$(wildcard source/seminar/$$*/*/*.gp))) \
	$$(wildcard source/seminar/$$*/*/meta.yaml) \
	source/seminar/$$*/meta.yaml ;

output/seminar/%/html-prerequisites: \
	$$(subst source/,output/,$$(wildcard source/seminar/$$*/*/*.jpg)) \
	$$(subst source/,output/,$$(wildcard source/seminar/$$*/*/*.png)) \
	$$(subst source/,output/,$$(subst .svg,.png,$$(wildcard source/seminar/$$*/*/*.svg))) \
	$$(subst source/,output/,$$(subst .gp,.png,$$(wildcard source/seminar/$$*/*/*.gp))) ;

output/seminar/%/problems.pdf: \
	modules/seminar/templates/problems.tex \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/problem.md))) \
	build/seminar/$$*/pdf-prerequisites \
	build/seminar/$$*/problems.tex
	$(call doubletex,seminar)

output/seminar/%/solutions.pdf: \
	modules/seminar/templates/solutions.tex \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/solution.md))) \
	build/seminar/$$*/pdf-prerequisites \
	build/seminar/$$*/solutions.tex
	$(call doubletex,seminar)

output/seminar/%/solutions-full.pdf: \
	modules/seminar/templates/solutions-full.tex \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/problem.md))) \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/solution.md))) \
	build/seminar/$$*/pdf-prerequisites \
	build/seminar/$$*/solutions-full.tex
	$(call doubletex,seminar)

output/seminar/%/instagram.pdf: \
	modules/seminar/templates/instagram.tex \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/problem.md))) \
	build/seminar/$$*/pdf-prerequisites \
	build/seminar/$$*/instagram.tex
	$(call doubletex,seminar)

output/seminar/%/semester.pdf: \
	modules/seminar/templates/semester.tex \
	$$(subst source/,build/,$$(subst .md,.tex,$$(wildcard source/seminar/$$*/*/*/problem.md))) \
	build/seminar/$$*/pdf-prerequisites \
	build/seminar/$$*/semester.tex
	$(call doubletex,seminar)

output/seminar/%/invite.pdf:\
	source/seminar/$$*/meta.yaml \
	build/seminar/$$*/invite.tex
	$(call doubletex,seminar)

output/seminar/%/semester-print.pdf: \
	output/seminar/$$*/semester.pdf
	@echo -e '$(c_action)Converting $(c_filename)$<$(c_action) to a short-edge booklet $(c_filename)$@$(c_action):$(c_default)'
	pdfbook --short-edge --quiet --outfile $@ $<

output/seminar/%/instagram: \
	output/seminar/$$*/instagram.pdf \
	$$(subst source/,output/,$$(subst .md,.png,$$(wildcard source/seminar/$$*/*/*/problem.md)))
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
	output/seminar/$$*/solutions ;

.PHONY:

output/seminar/%/copy: \
	output/seminar/%/
	$(eval words := $(subst /, ,$*))
	python3 ./dgs-copy.py $(word 1,$(words)) $(word 2,$(words)) $(word 3,$(words)) $(word 4,$(words)) $(user)
