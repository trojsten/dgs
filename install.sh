#!/bin/bash

DIR=$(dirname $0)
TEXHOME=`kpsewhich -var-value=TEXMFHOME`
mkdir -p $TEXHOME/tex/latex/
ln -s $PWD/core/tex/dgs.cls $TEXHOME/tex/latex/dgs.cls

sudo apt install texlive-full texlive-fonts-extra pandoc librsvg2-bin

echo Now download the appropriate pandoc-crossref and place it somewhere onto PATH
