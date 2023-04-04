rm -rf FontPro
git clone git@github.com:sebschub/FontPro.git FontPro
cd FontPro
mkdir otf
cp ../../core/fonts/MinionPro/*.otf otf/
./scripts/makeall MinionPro
sudo ./scripts/install
updmap-user --enable Map=MinionPro.map

