for f in `ls qt/*.ui`; do pyuic4 "$f" > "qt/`basename $f .ui`.py"; done
