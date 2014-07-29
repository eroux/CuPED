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

import os.path
import StringIO
import xml.etree.ElementTree as etree

import display
import transcript

class TemplateMetadataFile(object):
    def __init__(self):
        # The name of the file which should be copied or processed.
        self.input_file_name = None

        # The name (and location of the output file within the output
        # directory).
        self.output_file_name = None

        # Is this file a template to be processed (True), or should it be
        # copied into the output directory without processing (False)?
        self.should_be_processed = False

    def __xml__(self, indent = 0):
        # If this file should be processed, output it as a template.
        # Otherwise, if this file should just be included in the output, but
        # not processed, output it as an include.
        tag = 'template'
        if not self.should_be_processed:
            tag = 'include'

        # Define a quick function to help with indentation.
        def ind(str):
            return '%s%s' % ('    ' * indent, str)

        output = StringIO.StringIO()
        output.write(ind('<%s>\n' % tag))
        output.write(ind('    <input>%s</input>\n' % self.input_file_name))
        if self.output_file_name and \
           self.output_file_name != self.input_file_name:
            output.write(ind('    <output>%s</output>\n' % \
            self.output_file_name))
        output.write(ind('</%s>\n' % tag))

        return output.getvalue()

class TemplateMetadataVariable(object):
    # Acceptable values for 'type'.
    types = ['directory', 'file', 'transcript', 'string', 'colour', 'color',
             'font', 'tier', 'selection']

    def __init__(self):
        # The name under which this variable is to be presented to the user.
        self.name = None

        # A prose description of this variable's function, which will typically
        # be presented to the user.
        self.description = None

        # The type of this variable.  Required; possible values are listed in
        # 'TemplateMetadataVariable.types'.
        self.type = None

        # The name of a Python variable to which the value of this variable
        # should be assigned.  This name will be exposed to the templating
        # engine and to all subsequent Python code.
        self.destination = None

        # A dictionary containing additional options used to process this
        # (type of) variable.
        self.options = {}

        # The default choice(s) of values for this variable.
        self.default = None

        # The user's choice(s) of values for this variable.  (Note that this
        # is distinct from 'self.value': 'choice' is a list of strings,
        # representing the user's choices of values, and is serialized to XML
        # with the rest of these template variables.  'value', on the other
        # hand, is usually a list of non-string objects, and is not saved in
        # the serialized XML.
        self.choice = None

        # The range of possible choices for values of this variable.  This is
        # a Python expression which is evaluated by 'get_possible_choices()'
        # to return a list of triples of the form (choice_name,
        # choice_description, value).
        self.range = None

        # Condition under which the choices provided by the user for this
        # variable should be accepted.  This is a block of Python code which
        # is evaluated on the given choices, and which can raise a named error
        # if anything is wrong with them.  No return value is expected.
        self.condition = None

        # The name of another variable upon the value of which this variable
        # is dependent.  This is intended to support things like tiers found
        # in user-specified transcripts (which may or may not have been
        # supplied when a transcript is first loaded) and tier attributes
        # (which may not be relevant if a tier has not been given yet).
        # By default, no dependency is assumed to exist between any variables.
        self.dependency = None

        # The actual value(s) of this variable, as a list.  Clients of this
        # class should never assign values to this variable directly.  Instead,
        # to set a user's choice of values for this variable, use the
        # 'assign_choices()' function, which not only does the appropriate
        # error-checking, but, if successful, also updates this variable.
        self.value = None

    def is_constant(self):
        return 'isConstant' in self.options and self['isConstant'] == 'True'

    def get_possible_choices(self, env = {}):
        """ Returns a list of triples, where each triple is of the form
            (choice_name, choice_description, value), representing possible
            user choices for values of this variable.  This typically relies
            upon evaluation of 'self.range' to produce a list of possible
            values.  If no list of possible choices can be provided for this
            variable, None is returned."""

        # For selections, returning a list of triples is easy, since that's
        # what evaluating 'self.range' is supposed to produce.
        if self.type == 'selection':
            return eval(self.range, globals(), env)

        # For tiers, the situation is somewhat different: 'self.range' doesn't
        # evaluate to a list of triples, but rather a list of instantiated
        # transcript tiers.  Hence, we need to do a little conversion before
        # we return anything.
        elif self.type == 'tier':
            return [(t.name, \
                'Transcript tier (%d annotations, %d child tiers)' % \
                 (len(t.annotations), len(t.child_tiers)), t) for t in \
                  eval(self.range, globals(), env)]

        return None

    def assign_choices(self, choices, env = {}, unlist = False):
        """ Assigns the provided list of user choices for values of this
            variable.  If successful, each choice is processed into a value
            which can subsequently be accessed as 'self.value'.  If not
            successful, an Exception is raised."""

        # Retrieve global options for this variable and make sure their values
        # are reasonable.
        isRequired = True
        if 'isRequired' in self.options:
            isRequired = (self.options['isRequired'] == 'True')

        isConstant = False
        if 'isConstant' in self.options:
            isConstant = (self.options['isConstant'] == 'True')

        isOrdered = False
        if 'isOrdered' in self.options:
            isOrdered = (self.options['isOrdered'] == 'True')

        minSelection = 1
        if 'minSelection' in self.options:
            minSelection = int(self.options['minSelection'])

        maxSelection = 1
        if 'maxSelection' in self.options:
            maxSelection = int(self.options['maxSelection'])

        self.value = None

        if minSelection < 0:
            raise Exception, 'invalid value %d for minSelection' % minSelection
        elif maxSelection < 0:
            raise Exception, 'invalid value %d for maxSelection' % maxSelection
        elif maxSelection < minSelection:
            raise Exception, 'maxSelection is less than minSelection'

        # Enforce maximum and minimum selection sizes.
        if len(choices) > maxSelection:
            raise Exception, 'too many selections (max: %d)' % maxSelection
        elif len(choices) < minSelection:
            raise Exception, 'too few selections (min: %d)' % minSelection

        # Begin specific handling of each of the variable types.  (Consider
        # moving this behaviour to subclasses or delegates, maybe)

        # Directories.
        if self.type == 'directory':
            # Make sure that each directory exists.
            for choice in choices:
                if not os.path.isdir(choice):
                    raise Exception, '"%s" is not a directory' % choice

            self.choice = choices
            self.value = choices

        # Files.
        elif self.type == 'file':
            # Make sure that each file exists.
            for choice in choices:
                if not os.path.isfile(choice):
                    raise Exception, "'%s' is not a valid file" % choice

                if 'fileType' in self.options:
                    fileType = self.options['fileType']
# TODO: get these values from somewhere! (from a new 'cuped.py', which holds
#       the current AVTools instantiation?)
                    if fileType == 'image':
                        pass
                    elif fileType == 'audio':
                        pass
                    elif fileType == 'video':
                        pass
                    elif fileType == 'av':
                        pass
                    elif fileType == 'transcript':
                        pass
                    else:
                        raise Exception, "unknown file type '%s'" % fileType

            self.choice = choices
            self.value = choices

        # CuPED transcripts.
        elif self.type == 'transcript':
            # Make sure that the given file exists.
            for choice in choices:
                if not os.path.isfile(choice):
                    raise Exception, "'%s' is not a valid file" % choice

            # Load and parse the given transcripts.
            self.value = [transcript.Transcript(c) for c in choices]
            self.choice = choices

        # Arbitrary strings.
        elif self.type == 'string':
            # Retrieve string length conditions and sanity-check their values.
            minLength = -1
            if 'minLength' in self.options:
                minlength = int(self.options['minLength'])
                if minLength < 1:
                    raise Exception, 'invalid minLength value: %d' % minLength

            maxLength = -1
            if 'maxLength' in self.options:
                maxLength = int(self.options['maxLength'])
                if maxLength < 1:
                    raise Exception, 'invalid maxLength value: %d' % maxLength

            if minLength > maxLength:
                raise Exception, 'minLength greater than maxLength'

            for choice in choices:
                # Enforce string length restrictions.
                if minLength != -1 and len(choice) < minLength:
                    raise Exception, 'string "%s" is shorter than %d' % \
                        (choice, minLength)
                if maxLength != -1 and len(choice) > maxLength:
                    raise Exception, 'string "%s" is longer than %d' % \
                        (choice, maxLength)

            self.choice = choices
            self.value = choices

        # Colours.
        elif self.type == 'colour' or self.type == 'color':
            # Convert the 'rrggbb' hexadecimal colour strings into a list of
            # CuPEDColour objects.
            values = []
            for choice in choices:
                values.append(display.CuPEDColour(choice))

            self.choice = choices
            self.value = values

        # Fonts.
        elif self.type == 'font':
            # Convert the string representations of these fonts into a list of
            # CuPEDFont objects.
            values = []
            for choice in choices:
                values.append(display.CuPEDFont(choice))

            self.choice = choices
            self.value = values

        # Transcript tiers and generic selections between options.
        elif self.type == 'tier' or self.type == 'selection':
            # Retrieve a list of all of the options that could possibly be
            # chosen for this variable, as well as a list of their names.
            possible_choices = self.get_possible_choices(env)
            possible_names = [n for (n, d, v) in possible_choices]

            # Compile a list of tier objects that correspond to each of the
            # supplied tier names.
            values = []
            for choice in choices:
                if choice not in possible_names:
                    raise Exception, 'unknown option: "%s"' % choice
                values.append \
                    (possible_choices[possible_names.index(choice)][2])

            self.choice = choices
            self.value = values

        # Complain about all other types.
        else:
            self.value = None
            raise Exception, 'unknown variable type: "%s"' % self.type

        # Enforce any stated conditions on this variable's values.
        if self.condition:
            try:
                eval(self.condition)
            except Exception, reason:
                self.value = None
                raise Exception, reason

        # Enforce any requirement for this variable to have a value.
        if isRequired and self.value is None:
            raise Exception, 'value required for variable "%s"' % self.name

        # Unlist the value for this item, if requested.  (This assumes that
        # the value is currently a single-item list)
        if unlist:
            self.value = self.value[0]

    def __xml__(self, indent = 0):
        # Define a quick function to help with indentation.
        def ind(str):
            return '%s%s' % ('    ' * indent, str)

        # Prepare a buffer into which to write the XML representation of this
        # template metadata variable.
        output = StringIO.StringIO()
        output.write(ind('<variable>\n'))

        # Order in which the non-'options' fields should be listed.
        field_order = ['name', 'description', 'type', 'destination', \
            'range', 'condition', 'dependency']

        # Print out all variable fields (except 'options', which is more
        # complex, and is processed separately below).
        for field in field_order:
            field_val = self.__dict__[field]
            if field_val:
                output.write('    ')
                output.write(ind('<%s>%s</%s>\n' % (field, field_val, field)))

        # Print out 'default' and 'choice'.
        if self.default:
            output.write('    ')
            output.write(ind('<default>%s</default>\n' % self.default))

        if self.choice:
            output.write('    ')
            output.write(ind('<choice>%s</choice>\n' % self.choice))

        # Print out any options specified within this variable.
        for name in self.options:
            output.write('    ')
            output.write(ind('<option name="%s">%s</option>\n' % \
                         (name, self.options[name])))

        output.write(ind('</variable>\n'))
        return output.getvalue()

class TemplateMetadata(object):
    def __init__(self, template_metadata_file = None):
        # The name of this template package.
        self.name = None

        # A prose description of this template package.
        self.description = None

        # A list of tuples containing information about contributors to the
        # development of this CuPED template package.  Tuples are of the form
        # (contributor_name, contributor_role).
        self.contributors = []

        # The license under which this template package is being released.
        self.license = None

        # The version number of this release of the template package.
        self.version = None

        # The MIME type and name of the output file which should serve as a
        # preview.
        self.preview_mime_type = None
        self.preview_file_name = None

        # The directory in which template files and resources are found.
        # (This string can contain the variable '%CuPED%', which will be
        #  expanded at run-time to represent the path of the current CuPED
        #  installation)
        self.input_directory = None

        # The directory into which output files should be placed.  (This
        # string can contain the variable '%CuPED%', which will be expanded
        # at run-time to represent the path of the current CuPED installation)
        self.output_directory = None

        # A list of TemplateMetadataVariable objects, representing the options
        # exposed to the (Mako) template(s).
        self.variables = []

        # A list of TemplateMetadataFile objects, representing the files
        # which should be processed and/or included in the output.
        self.templates = []

        # If an input file has been provided, attempt to parse it into the
        # fields of this new object.
        if template_metadata_file:
            # Load the template metadata file.
            tree = etree.parse(template_metadata_file)
            root = tree.getroot()

            def request(element, name):
                elem = element.find(name)
                if elem is not None and elem.text:
                    return (''.join(["%s " % x.strip() for x in \
                        elem.text.splitlines()])).strip()

                return ''

            def require(element, name):
                elem = element.find(name)
                if elem is not None and elem.text:
                    return (''.join(["%s " % x.strip() for x in \
                        elem.text.splitlines()])).strip()

                raise ValueError, 'no value for "%s"' % name

            # Load the mandatory and optional fields in this template metadata
            # file.
            self.name = require(root, 'name')
            self.description = request(root, 'description')
            self.license = request(root, 'license')
            self.version = request(root, 'version')

            # Load in the list of contributors to this template metadata file.
            for contrib in root.findall('contributor'):
                contributor_name = contrib.attrib['name']
                contributor_role = contrib.attrib['role']
                self.contributors.append((contributor_name, contributor_role))

            # Load in the input and output directories.  If not defined,
            # default to the CuPED directory.
            self.input_directory = request(root, 'input_directory')
            if not self.input_directory:
                self.input_directory = os.path.dirname(__file__)

            self.output_directory = request(root, 'output_directory')
            if not self.output_directory:
                self.output_directory = os.path.dirname(__file__)

            # Load in the variables defined in the template metadata file.
            for var in root.findall('variables/variable'):
                tmv = TemplateMetadataVariable()

                # Load the mandatory values for 'destination' and 'type'.
                tmv.destination = require(var, 'destination')
                tmv.type = require(var, 'type')

                # Load the optional values (and supply default values for them,
                # where necessary).
                tmv.name = request(var, 'name')
                tmv.description = request(var, 'description')
                tmv.range = request(var, 'range')
                tmv.condition = request(var, 'condition')
                tmv.dependency = request(var, 'dependency')

                # Both 'default' and 'choice' can be either simple, unquoted
                # string values (which are unlikely to evaluate successfully),
                # or Python lists of strings, represented in string format.
                #
                # Either way, we need to make sure that they end up as lists
                # of strings.  Hence, try to evaluate them: if they come out
                # as lists, good.  Otherwise, treat them as strings.
                tmv.default = request(var, 'default')
                if tmv.default:
                    try:
                        default = eval(tmv.default)
                        if default != list(default): raise Exception
                        tmv.default = default
                    except:
                        tmv.default = [tmv.default]
                else:
                    tmv.default = []

                tmv.choice = request(var, 'choice')
                if tmv.choice:
                    try:
                        choice = eval(tmv.choice)
                        if choice != list(choice): raise Exception
                        tmv.choice = choice
                    except:
                        tmv.choice = [tmv.choice]
                else:
                    tmv.choice = []

                # Load in the list of options, if any.
                for option in var.findall('option'):
                    tmv.options[option.attrib['name']] = option.text

                # Assign values to constants.
                if tmv.is_constant():
                    if tmv.choice:
                        tmv.assign_choices(tmv.choice)
                    elif tmv.default:
                        tmv.assign_choices(tmv.default)

                self.variables.append(tmv)

            # Load in the files defined in the template metadata file.
            for file in root.find('templates'):
                tmf = TemplateMetadataFile()
                tmf.should_be_processed = (file.tag == 'template')
                tmf.input_file_name = file.find('input').text

                output = file.find('output')
                if output is None:
                    tmf.output_file_name = tmf.input_file_name
                else:
                    tmf.output_file_name = output.text

                self.templates.append(tmf)

            # Load in the preview information, if available.
            preview = root.find('preview')
            if preview is not None:
                self.preview_mime_type = preview.attrib['type']
                self.preview_file_name = preview.text

    def __xml__(self):
        # Create a string buffer for the XML output and write the header.
        output = StringIO.StringIO()
        output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        output.write('<template version="1.0">\n')

        # Write out each field in the template metadata (except for the more
        # complex variables) in the preferred order.
        display_order = \
            ['name', 'description', 'license', 'version', \
             'input_directory', 'output_directory']
        for key in display_order:
            val = self.__dict__[key]
            if val:
                output.write('    ')
                output.write('<%s>%s</%s>\n' % (key, val, key))

        # Write out the preview information, if available.
        if self.preview_file_name and self.preview_mime_type:
            output.write('    ')
            output.write('<preview type="%s">%s</preview>\n' % \
                (self.preview_mime_type, self.preview_file_name))

        # Write out the list of contributors.
        for (name, role) in self.contributors:
            output.write('    ')
            output.write('<contributor name="%s" role="%s" />\n' % (name, role))

        # Write out the variables.
        output.write('    ')
        output.write('<variables>\n')
        for var in self.variables:
            output.write(var.__xml__(indent = 2))

        output.write('    ')
        output.write('</variables>\n')

        # Write out the list of files.
        output.write('    ')
        output.write('<templates>\n')
        for file in self.templates:
            output.write(file.__xml__(indent = 2))

        output.write('    ')
        output.write('</templates>\n')

        # Write out the file footer.
        output.write('</template>')
        return output.getvalue()


# Extremely weak, ad-hoc unit tests.  FIXME
if __name__ == '__main__':
    import tempfile
    templates = ['templates/BasicTemplate/BasicTemplate.xml', \
        'templates/FlowplayerTemplate/FlowplayerTemplate.xml']
    for template in templates:
        x = TemplateMetadata(template)
        x_xml = x.__xml__()

        buffer = tempfile.TemporaryFile()
        buffer.write(x_xml)
        buffer.seek(0)

        y = TemplateMetadata(buffer)
        y_xml = y.__xml__()

        buffer2 = tempfile.TemporaryFile()
        buffer2.write(y_xml)
        buffer2.seek(0)

        z = TemplateMetadata(buffer2)
        z_xml = z.__xml__()

        # Make sure that we can round-trip the XML.
        print '%s: x_xml == y_xml: %s' % (template, x_xml == y_xml)
        print '%s: y_xml == z_xml: %s' % (template, y_xml == z_xml)
        print '%s: x_xml == z_xml: %s' % (template, x_xml == z_xml)
        print ''

        buffer.close()
        buffer2.close()
