CuPED
=====

Customizable Presentation of ELAN Documents (non official!)

CuPED ("Customizable Presentation of ELAN Documents") transforms time-aligned
XML transcripts produced with ELAN (EUDICO Linguistic Annotator; MPI Nijmegen) 
and their associated media into other file formats.

CuPED is written in Python, and distributed under the GNU General Public
License, Version 2 (see 'LICENSE').  Certain software components used by
CuPED may be released under other licenses; see CREDITS for more information.

## About this repository ##

This repository is a fork of the original project, it has not been approved
by the original authors. If you want an official version, please visit
the [official website](http://sweet.artsrn.ualberta.ca/cdcox/cuped/).

### Purpose ###

I made this repository to help a friend who needed CuPED and couldn't make it
work under Windows 8. As he had a Linux installation, the idea was to make
the install and launch process cleaner for Linux. I did not test Windows or OSX
install process, for the simple reason that I don't own valid licenses for
these OSs (but contributions are welcome !).

I'm not willing to be a maintainer of this repository, for the simple reason
that I don't use this software myself.

### Changelog ###

First commit is the initial state of 0.3.15 version.

### Installation ###

To run CuPED under Linux, please install the following:

 * python 2.x
 * python-qt4
 * pyqt4-dev-tools
 * python-mako
 * ffmpeg
 * yamdi
 
All are available under Debian.

Then run `./compile.sh` to compile the .ui files into python.

### Running ###

Once installed, run `./src/cuped-cli` or `./src/cuped-qt`.
