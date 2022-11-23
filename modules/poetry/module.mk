.SECONDEXPANSION:

# Build scripts for language and venue prerequisites

# % <competition>/<volume>/venues/<venue>
input/poetry/%/columns.tex: \
	modules/poetry/templates/base.tex \
	$$(wildcard source/poetry/%/*/*.md)



