# CSV plotting script file for gnuplot(1). Opens file "../../data/data.csv",
# filters lines using awk(1), and plots values on screen. File is re-read every
# second. You may want to use tail(1) instead of cat(1) to plot only the last x
# values. Edit "filter.awk" and change print command to the desired columns.
#
# Run with:
# $ gnuplot -p plot.plt
set autoscale
set xtic auto
set ytic auto
set xlabel "Time"
set timefmt "%Y-%m-%dT%H:%M:%S"
set format x "%H:%M"
set xdata time
set ylabel "Y"
set terminal x11 0
set nokey
set grid
set title 'Plot'
# plot "< tail -n 25 ../data/data.csv | awk -f filter.awk" using 1:2 with lines
plot "< cat ../../data/data.csv | awk -f filter.awk" using 1:2 with lines
pause 1
reread