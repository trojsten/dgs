#!/bin/bash

sudo apt install texlive-full texlive-fonts-extra pandoc librsvg2-bin gnuplot

DIR=$(dirname $0)
TEXHOME=`kpsewhich -var-value=TEXMFHOME`
mkdir -p $TEXHOME/tex/latex/
ln -s $PWD/core/latex/dgs.cls $TEXHOME/tex/latex/dgs.cls

cd assets/fonts/
rm -rf FontPro
git clone git@github.com:sebschub/FontPro.git FontPro
cd FontPro
mkdir otf
cp ../../fonts/MinionPro/*.otf otf/
./scripts/makeall MinionPro
yes | sudo ./scripts/install
yes | updmap-user --enable Map=MinionPro.map

