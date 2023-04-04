mkdir otf
cp ../../core/fonts/MinionPro/*.otf otf/
./scripts/makeall MinionPro
./scripts/install
sudo updmap-sys --enable Map=MinionPro.map

