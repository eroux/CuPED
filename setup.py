#!/usr/bin/env python
#
# Copyright (c) 2008-2009 CuPED project.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02111, USA.

"""
py2app/py2exe build script for CuPED.

Based on the build script provided in the 'py2app' documentation: 
http://svn.pythonmac.org/py2app/py2app/trunk/doc/index.html

Usage (Mac OS X):
    python setup.py py2app

Usage (Windows):
    python setup.py pyexe
"""

import ez_setup
ez_setup.use_setuptools()

import os
import shutil
import sys
from setuptools import setup

# Add the CuPED package to sys.path.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
import cuped.settings

# Dummy class, used to skirt around problems with cross-platform builds.
class custompy2app:
    pass

# Build variables.
pkg_name = 'CuPED'
description = 'CuPED: Customizable Presentation of ELAN Documents'
url = 'http://sweet.artsrn.ualberta.ca/cdcox/cuped'
version = cuped.settings.Settings().getVersion()
mainscript = 'src/cli/main.py'

# Get a list of all the files in the 'templates' directory.
templates = []
def ss(str):
    if os.altsep: return str.replace(os.sep, os.altsep)
    return str

for (dirpath, dirnames, filenames) in os.walk('templates'):
    dirpath = ss(dirpath)
    if filenames:
        fnames = [ss(os.path.join(dirpath, f)) for f in filenames]
        templates.append((dirpath, fnames))

# Data files to be bundled with the application.
data_files = templates


# Darwin / Mac OS X
if sys.platform == 'darwin':
    # Add platform-specific binaries.
    data_files.append(('bin/osx', ['bin/osx/ffmpeg', 'bin/osx/yamdi']))
    extra_options = dict(
        setup_requires = ['py2app'],
        app = [mainscript],
        data_files = data_files,

        # Cross-platform applications generally expect sys.argv to be used
        # for opening files.
        options = dict(
            py2app = {
                'strip' : True,
                'optimize' : 2,
                'iconfile' : 'bin/icons/cuped/Cupedlotsofhearts.icns',
                'argv_emulation' : True,
                'plist' : {
                    'CFBundleName' : pkg_name,
                    'CFBundleShortVersionString' : version,
                    'CFBundleGetInfoString' : '%s %s' % (pkg_name, version),
                    'CFBundleExecutable' : pkg_name,
                    'CFBundleIdentifier' : 'ca.ualberta.cuped'
                },
            },
        )
    )

    # A customized build class, used to create a disk image out of the final
    # py2app stand-alone distribution.
    from py2app.build_app import py2app
    class custompy2app(py2app):
        def run(self):
            # Run the regular build process.
            py2app.run(self)

            # Remove debug libraries from the application.
            app_loc = os.path.join(self.dist_dir, '%s.app' % pkg_name)
            os.system('find %s -iname "*.prl" -delete' % app_loc)
            os.system('find %s -iname "*_debug" -delete' % app_loc)

            # Prepare the application for OSX deployment using 'macdeployqt'.
            # (This should kill off the 'two sets of Qt binaries' warning that
            # otherwise haunts console output)
            os.system('macdeployqt %s' % app_loc)

            # Set permissions on platform-specific binaries.
            bdir = os.path.join(app_loc, 'Contents', 'Resources', 'bin', 'osx')
            os.system('chmod a+x %s' % os.path.join(bdir, 'ffmpeg'))
            os.system('chmod a+x %s' % os.path.join(bdir, 'yamdi'))

            # Create a compressed disk image of the final program.  Cf.:
            # http://svn.xiph.org/trunk/ffmpeg2theora/frontend/setup.macosx.py
            name = '%s %s' % (pkg_name, version)
            dmgPathTemp = os.path.join(self.dist_dir, "%s.tmp.dmg" % name)
            dmgPath = os.path.join(self.dist_dir, '%s.dmg' % name)

            # Create the basic disk image.
            os.system('hdiutil create -srcfolder "%s" -volname "%s" -format UDRW "%s"' % (self.dist_dir, name, dmgPathTemp))

            # Copy the custom background, icon, and .DS_Store into the disk
            # image, making each file invisible.
            os.system('hdiutil attach -autoopen "%s"' % dmgPathTemp)
            os.mkdir('/Volumes/%s/.background' % name)
            shutil.copy('bin/osx/dmg/dmg_background.png', \
                '/Volumes/%s/.background/folder.png' % name)
            shutil.copy('bin/osx/dmg/dmg_DS_Store', \
                '/Volumes/%s/.DS_Store' % name)
            shutil.copy('bin/osx/dmg/dmg_icon.icns', \
                '/Volumes/%s/.VolumeIcon.icns' % name)
            os.system('ln /Applications "/Volumes/%s/"')
            os.system('SetFile -a V "/Volumes/%s/.background"' % name)
            os.system('SetFile -a V "/Volumes/%s/.DS_Store"' % name)
            os.system('SetFile -a V "/Volumes/%s/.VolumeIcon.icns"' % name)

            # Create an alias in the disk image to the local "Applications"
            # folder.
            os.system('ln -s /Applications "/Volumes/%s/Applications"' % name)
            os.system('SetFile -P -a A "/Volumes/%s/Applications"' % name)

            # Activate the custom folder icon, and have the disk image open
            # in a new Finder window when mounted.
            os.system('SetFile -a C "/Volumes/%s"' % name)
            os.system('bless -openfolder "/Volumes/%s/"' % name)

            # Detach the temporary disk image, then compress it to form the
            # final disk image.
            os.system('hdiutil detach "/Volumes/%s"' % name)
            os.system('hdiutil convert -format UDRW -imagekey zlib-level=9 -o "%s" "%s"' % (dmgPath, dmgPathTemp))
            os.remove(dmgPathTemp)

# Windows
elif sys.platform == 'win32':
    # Add platform-specific binaries.
    data_files.append( \
        ('bin/win32', ['bin/win32/ffmpeg.exe', 'bin/win32/yamdi.exe']))

    import py2exe
    extra_options = dict(
        setup_requires = ['py2exe'],
        data_files = data_files,

        # Create an executable where the Python DLL is not bundled.
        options = {
            'py2exe' : {
                'bundle_files' : 2,
                'includes' : ['cuped', 'mako.cache'],
            }
        },
        zipfile = None,

        # Either 'console' (CLI app) or 'windows' (GUI app).
        console = [{
            'script': mainscript,
            'icon_resources': [(0, 'bin/icons/cuped/Cupedlotsofhearts.ico')]
        }],
    )
else:
    extra_options = dict(
        # Normally Unix-like platforms will use "setup.py install" and
        # install the main script as such.
        scripts = [mainscript],
    )

setup(
    name = pkg_name,
    version = version,
    description = description,
    url = url,
    cmdclass = {'py2app': custompy2app},
    **extra_options
)
