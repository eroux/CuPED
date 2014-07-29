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

import os
import ConfigParser

class Settings(object):
    _version = '0.3.15'

    def __new__(cls, config_file = None, *args, **kwargs):
        # Singleton class.
        if not '_instance' in cls.__dict__:
            cls._instance = object.__new__(cls)

            # Create a new ConfigParser.
            cls._config = ConfigParser.SafeConfigParser()
            if config_file:
                cls._config_file = config_file
            else:
                cls._config_file = os.path.expanduser('~/.cupedrc')

            # Try to load the default configuration file, if it exists.  If it
            # doesn't, try to create one.
            try:
                cls._config.readfp(open(cls._config_file))
            except:
                # Write the new configuration file to disk.
                output = open(cls._config_file, 'w')
                cls._config.write(output)
                output.close()

        return cls._instance

    def set(self, section, name, value):
        """
        Sets the value of the named setting in the given section.  If the
        given section doesn't exist in the configuration file, a new section
        with the given name is created automatically.
        """
        if not self._config.has_section(section):
            self._config.add_section(section)

        self._config.set(section, name, value)

    def get(self, section, name):
        """
        Returns the current value of the given setting in the given section.
        If the given section doesn't exist, or the given setting doesn't exist
        within that section, None is returned.
        """
        if not self._config.has_section(section):
            return None

        if self._config.has_option(section, name):
            return self._config.get(section, name)

    def remove(self, section, name):
        """Removes the given setting in the given section, if it exists."""
        if self._config.has_option(section, name):
            self._config.remove_option(section, name)

    def getSection(self, section):
        """
        Returns a list of (name, value) tuples, representing the settings in
        the given section.
        """
        if not self._config.has_section(section):
            return []

        return self._config.items(section)

    def save(self):
        """Writes the current settings to the CuPED configuration file."""
        output = open(self._config_file, 'w')
        self._config.write(output)
        output.close()

    def getVersion(self):
        """Returns the current version of CuPED."""
        return self._version
