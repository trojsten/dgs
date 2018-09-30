MAKEFLAGS += --no-builtin-rules

.SECONDEXPANSION:

output/scholar/handout/%.pdf: \
	input/scholar/handout/%.tex

.PHONY:

output/seminar/%/copy: \
	output/seminar/%/all
	$(eval words := $(subst /, ,$*))
	python3 ./dgs-copy.py $(word 1,$(words)) $(word 2,$(words)) $(word 3,$(words)) $(word 4,$(words))
