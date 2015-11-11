set datafile separator ","
set key off
set grid
set yrange[0:25]
set xrange[50:110]
set xlabel "T / °C"
set ylabel "Δm / g"
set title "Závislosť prírastku hmotnosti špagiet od hmotnosti"
plot "task4-data1.csv" pt 7 ps 0.8
