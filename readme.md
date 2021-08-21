This is DGS, short for Trojsten Document Generation System (pronounced "degeš").

## Hacks

### Create symlinks to pictures in Náboj
cd <volume>/languages/slovak/
find . -name "*.svg" -exec ln -s -T ../../slovak/{} ../<language>/{} \;
