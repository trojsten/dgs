set terminal eps
set key off
set grid
set output "graaf2.eps"
set yrange[40:80]
set xrange[0:1400]
set xlabel "t / s"
set ylabel "Δm / g"
set title "Závislosť prírastku hmotnosti špagiet od času"
f(x) = 90<x && x<1220 ? A*x+B: 1/0
fit f(x) "data2.txt" via A, B
plot "data2.txt" pt 7 ps 0.8, f(x) lt rgb "red"