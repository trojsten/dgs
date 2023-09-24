#!/bin/bash

DIR=$(dirname $0)
TEXHOME=`kpsewhich -var-value=TEXMFHOME`
mkdir -p $TEXHOME/tex/latex/
ln -s $PWD/core/tex/dgs.cls $TEXHOME/tex/latex/dgs.cls

sudo apt install texlive-full texlive-fonts-extra pandoc librsvg2-bin

cd core/fonts/
rm -rf FontPro
git clone git@github.com:sebschub/FontPro.git FontPro
cd FontPro
mkdir otf
cp ../../fonts/MinionPro/*.otf otf/
./scripts/makeall MinionPro
yes | sudo ./scripts/install
yes | updmap-user --enable Map=MinionPro.map

