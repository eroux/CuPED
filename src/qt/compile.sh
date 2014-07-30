for f in `ls *.ui`; do pyuic4 "$f" > "`basename $f .ui`.py" done
