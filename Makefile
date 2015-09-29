all: do-tasks

do-tasks:
	xelatex -jobname=tasky -halt-on-error tasks.tex
	evince tasky.pdf &
