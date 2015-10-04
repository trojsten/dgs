set terminal eps
set key off
set grid
set output "graaf1.eps"
set yrange[0:25]
set xrange[50:110]
set xlabel "T / °C"
set ylabel "Δm / g"
set title "Závislosť prírastku hmotnosti špagiet od hmotnosti"
plot "data1.txt" pt 7 ps 0.8