#!/bin/bash

DIR=$(dirname $0)
TEXHOME=`kpsewhich -var-value=TEXMFHOME`
mkdir -p $TEXHOME/tex/latex/
ln -s $PWD/core/tex/dgs.cls $TEXHOME/tex/latex/dgs.cls

sudo apt install pandoc librsvg2-bin
