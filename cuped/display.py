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

import re
import StringIO

class CuPEDColour(object):
    def __init__(self, str = None):
        # The red component of this colour [0-255].
        self.red = 0

        # The blue component of this colour [0-255].
        self.blue = 0

        # The green component of this colour [0-255].
        self.green = 0

        # If a string representation of a colour has been provided, attempt
        # to parse it into the fields of this object.
        if str:
            self.load(str)

    def load(self, str):
        """Parses the given colour string into the fields of this object."""
        try:
            if str.startswith('#'):
                str = str[1:]

            self.red = int(str[0:2], 16)
            self.green = int(str[2:4], 16)
            self.blue = int(str[4:6], 16)
        except:
            raise Exception, 'invalid colour string: "%s"' % str

    def __str__(self):
        return '#%02x%02x%02x' % (self.red, self.green, self.blue)

class CuPEDFont(object):
    def __init__(self, str = None):
        # The name of this font.
        self.font_name = None

        # The size of this font (in pt).
        self.font_size = -1

        # Is this font to be displayed in bold?
        self.is_bold = False

        # Is this font to be displayed in italics?
        self.is_italic = False

        # Should this font be underlined?
        self.is_underline = False

        # Should this font be displayed with a strike-through line?
        self.is_strike_through = False

        # Should this font be displayed in small caps?
        self.is_small_caps = False

        # If a font string has been provided, attempt to parse it into the
        # fields of this CuPEDFont object.
        if str:
            self.load(str)

    def load(self, str):
        """Parses the given font-string into the fields of this object."""
        try:
            font_pattern = re.compile(r'''
                "(.*?)"\s*:\s*                   # "Font name":
                size\s*=\s*(.*?)\s*pt\s*         # size = xx pt
                ''', re.IGNORECASE | re.VERBOSE)
            match = font_pattern.match(str)
            (name, size) = match.groups()

            self.font_name = name
            self.font_size = float(size)

            remainder = str[match.end():]
            self.is_bold = ('bold' in remainder)
            self.is_italic = ('italic' in remainder)
            self.is_underline = ('underline' in remainder)
            self.is_strike_through = ('strikethrough' in remainder)
            self.is_small_caps = ('smallcaps' in remainder)
        except:
            raise Exception, 'invalid font string: %s' % str

    def __str__(self):
        output = StringIO.StringIO()
        output.write('"%s": ' % \
            (self.font_name.replace('\\', '\\\\').replace('"', '\\"')))

        if int(self.font_size) != self.font_size:
            output.write('size = %.1fpt' % self.font_size)
        else:
            output.write('size = %dpt' % self.font_size)

        if self.is_bold:
            output.write(', bold')

        if self.is_italic:
            output.write(', italic')

        if self.is_underline:
            output.write(', underline')

        if self.is_strike_through:
            output.write(', strikethrough')

        if self.is_small_caps:
            output.write(', smallcaps')

        return output.getvalue()

# Extremely weak, ad-hoc unit tests.
if __name__ == '__main__':
    colours = ['#ffeeaa', '#223344', '#123456']
    for colour in colours:
        c = CuPEDColour(colour)
        print 'input colour == output colour: %s' % (colour == c.__str__())
        print " * input  = %s" % colour
        print " * output = %s" % c.__str__()
    print ""

    fonts = ['"Times New Roman": size = 12pt', \
        '"Doulos SIL": size = 14pt, bold, italic, smallcaps', \
    ]
    for font in fonts:
        f = CuPEDFont(font)
        print 'input font == output font: %s' % (font == f.__str__())
        print " * input  = '%s'" % font
        print " * output = '%s'" % f.__str__()
    print ""
