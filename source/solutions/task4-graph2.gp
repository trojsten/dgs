set datafile separator ","
set key off
set grid
set yrange[40:80]
set xrange[0:1400]
set xlabel "t / s"
set ylabel "Δm / g"
set fit quiet
set fit logfile "/dev/null"
f(x) = 90<x && x<1220 ? A*x+B: 1/0
fit f(x) "task4-data2.csv" via A, B
plot "task4-data2.csv" pt 7 ps 0.8, f(x) lt rgb "red"

