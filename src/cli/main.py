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

import copy
import optparse
import os
import shutil
import sys
import traceback

import mako.template

# Hackishly add the CuPED package to sys.path, if needed.
try:
    sys.path.append(os.path.abspath( \
        os.path.join(os.path.dirname(__file__), os.pardir)))
except NameError:
    pass

import cuped.avtools
import cuped.template
import cuped.display


# Get an implementation of the 'avtools' interface.  This will be passed on to
# the templating engine later under the name 'av'.
avtools = cuped.avtools.AVTools()

# Parse command-line options.
usage = 'Usage: %prog [options] template1.xml template2.xml ...'
parser = optparse.OptionParser(usage = usage)
parser.add_option('-d', '--debug', action = 'store_true', default = False, \
    help = 'enable debug mode, printing processed templates to stdout')
parser.add_option('-o', '--output', action = 'append', dest = 'output', \
    help = 'save the expanded template metadata', default = [])
parser.add_option('-p', '--always-prompt', action = 'store_true', \
    dest = 'always_prompt', default = False, \
    help = 'prompt for values even when values exist in the template metadata')
parser.add_option('-v', '--override', action = 'append', dest = 'overrides', \
    help = 'override a variable\'s value (e.g. -v "variable:new_value")', \
    default = [])
parser.add_option('-z', '--dry-run', action = 'store_true', \
    dest = 'dry_run', default = False, \
    help = "don't process any templates or create any directories")

(options, args) = parser.parse_args()

# Quick sanity check: has an output file been specified for each template
# metadata file given as a command-line argument?
if len(options.output) > 0 and len(options.output) != len(args):
    parser.error('output files not specified for all template metadata files')
    sys.exit(1)

# Compile a dictionary of overridden variables, mapping variable destination
# names to their "raw" (i.e. uneval()uated string) choices.
overrides = \
    dict([tuple(override.split(':', 1)) for override in options.overrides])

# Load and process each of the template metadata files in turn.
for input_template in args:
    try:
        template_metadata = cuped.template.TemplateMetadata(input_template)
    except Exception, reason:
        print 'ERROR: can\'t load "%s" (%s)' % (input_template, reason)
        traceback.print_exc(file = sys.stdout)
        sys.exit(1)

    # The directory in which this template metadata file is located is treated
    # as the base directory for all input files specified from here on in.
    cuped_directory = os.path.abspath(os.curdir)
    input_directory = template_metadata.input_directory.replace('%CuPED%', \
        cuped_directory)
    if not os.path.exists(input_directory):
        input_directory = os.path.abspath(os.path.dirname(input_template))

    # If the output directory doesn't exist, create it (or die trying).
    output_directory = template_metadata.output_directory.replace('%CuPED%', \
        cuped_directory)
    if not os.path.exists(output_directory) and not options.dry_run:
        os.mkdir(output_directory)

    # Make sure that the output of any media processing goes into the
    # specified output directory.
    avtools.set_output_directory(output_directory)

    # Now parse the variables out of the template metadata and prompt the user
    # (where appropriate) to supply values for each one.
    variables = {}
    for variable in template_metadata.variables:
        # If this variable is a constant, then skip asking the user to provide
        # a value for it.
        successful = False
        if variable.is_constant():
            successful = True

        # See if a value was specified for this variable on the command line.
        # If so, use that value, rather than prompting the user for input.
        if variable.destination in overrides:
            # This is no less dangerous than any other time users are able to
            # provide arbitrary code to eval(), but it still bothers me.
            try:
                value = \
                    eval(overrides[variable.destination], globals(), variables)
            except Exception:
                value = overrides[variable.destination]

            if value != list(value):
                value = [value]

            # Attempt to assign the override value to this variable.  If the
            # override is invalid, make the user provide a value interactively.
            try:
                variable.assign_choices(value, variables)
                successful = True
            except Exception, reason:
                print 'ERROR: invalid override: "%s" (%s)' % (value, reason)

        # If a value for this variable can be taken from the template metadata,
        # then use that, only bugging the user about this if required to.
        if variable.choice and not options.always_prompt:
            try:
                variable.assign_choices(variable.choice, variables)
                successful = True
            except Exception, reason:
                print 'ERROR: invalid choice(s): "%s" (%s)' % \
                    (variable.choice, reason)

        # Loop until we've successfully gotten a value for this variable.
        while not successful:
            # Print a prompt.
            print '\n%s: %s' % (variable.name, variable.description)

            possible_choices = variable.get_possible_choices(variables)
            if possible_choices:
                print 'Possible choices:'
                for (name, description, value) in possible_choices:
                    print ' * "%s" - %s' % (name, description)

            if variable.choice:
                print 'Current choice(s): %s' % variable.choice

            if variable.default:
                print 'Choice [default: "%s"]:' % variable.default,
            else:
                print 'Choice:',

            # Get some input from the user.  If the user doesn't enter a
            # value, and if there's a default value available, use that,
            # instead.
            choice = raw_input('')
# TODO: this obviously isn't going to cut it in cases where the user is
#       expected to select multiple values.  Fix this to allow multiple
#       selections.  FIXME
            if not choice and variable.default:
                choice = variable.default

# TODO: quick hack to wrap the single choice in a list.  remove this later
#       once users are able to specify multiple values for an option.
            if choice != list(choice):
                choice = [choice]

            # See if this is a valid choice.  If so, break out of the loop and
            # move on to processing the next variable.  Otherwise, report the
            # error to the user and try for input one more time.
            try:
                variable.assign_choices(choice, variables)
                successful = True
            except Exception, reason:
                print 'ERROR: invalid choice (%s)' % reason

            # If this is a 'tier' variable, we should find out if the user
            # wants to provide display attributes, too.
            if variable.type == 'tier':
                print 'Configure tier display attributes? (y/n) ',
                configure_display = raw_input()
                if configure_display and configure_display[0].lower() == 'y':
                    tiers = variable.value
                    if type(tiers) != type([]):
                        tiers = [tiers]

                    # Run through each of the tiers.
                    for tier in tiers:
                        tname = tier.name
                        print 'Tier "%s"' % tname

                        # Ask the user for fonts.
                        counter = 1
                        fonts = []
                        while True:
                            print ' * Tier font #%d:' % counter,
                            font = raw_input()
                            if not font:
                                break

                            try:
                                # Make sure this is a valid font.  If it is,
                                # add the string to our running list of fonts
                                # and prompt the user to enter another font.
                                f = cuped.display.CuPEDFont(font)
                                fonts.append(font)
                                counter = counter + 1
                            except Exception, reason:
                                print ' ** Invalid choice (%s)' % reason

                        # Convert all of these fonts into a single
                        # TemplateMetadataVariable.
                        if len(fonts) > 0:
                            fv = cuped.template.TemplateMetadataVariable()
                            fv.type = 'font'
                            fv.name = '"%s" tier font(s)'  % tname
                            fv.options['maxSelection'] = '%d' % len(fonts)
                            fv.options['tierDisplayVariable'] = tname
                            fv.description = 'Font(s) for tier "%s"' % tname
                            fv.destination = 'filter(lambda x: x.name == "%s", %s)[0].fonts' % (tname, variable.range)
                            fv.dependency = variable.name

                            try:
                                fv.assign_choices(fonts, variables)
                                template_metadata.variables.append(fv)
                            except Exception:
                                print 'ERROR: Unable to assign fonts!'
                                traceback.print_exc(file = sys.stdout)

                        # Ask the user for a background colour.
                        while True:
                            print ' * Tier background colour:',
                            colour = raw_input()
                            if not colour:
                                break

                            try:
                                # Create a new variable to represent this
                                # colour choice.
                                cv = cuped.template.TemplateMetadataVariable()
                                cv.type = 'colour'
                                cv.name = '"%s" tier background colour' % tname
                                cv.options['tierDisplayVariable'] = tname
                                cv.description = \
                                    'Background colour for tier "%s"' % tname
                                cv.destination = 'filter(lambda x: x.name == "%s", %s)[0].background_colour' % (tname, variable.range)
                                cv.dependency = variable.name

                                # Make sure that this is a valid colour.  If
                                # not, this will raise an Exception.
                                cv.assign_choices([colour], variables)
                                template_metadata.variables.append(cv)
                                break
                            except Exception, reason:
                                print ' ** Invalid choice (%s)' % reason

                        # Ask the user whether or not this tier should be
                        # displayed.
                        while True:
                            print ' * Tier is visible (default: yes)? (y/n)',
                            visible = raw_input()
                            if not visible:
                                break

                            visible = visible[0].lower()
                            if visible == 'y':
                                # The default is that tiers are visible -- no
                                # need to remember this.
                                break
                            elif visible == 'n':
                                # If the tier is not supposed to be shown, we
                                # need to record this choice in a variable
                                # that can be serialized to XML with the rest
                                # of the template.
                                vv = cuped.template.TemplateMetadataVariable()
                                vv.type = 'selection'
                                vv.name = '"%s" tier visibility' % tname
                                vv.options['tierDisplayVariable'] = tname
                                vv.description = 'Is tier "%s" visible?' % tname
                                vv.destination = 'filter(lambda x: x.name == "%s", %s)[0].is_visible' % (tname, variable.range)
                                vv.range = "[('Yes', 'Yes, this tier is visible', True), ('No', 'No, this tier is not visible', False)]"
                                vv.dependency = variable.name

                                vv.assign_choices(['No'], variables)
                                template_metadata.variables.append(vv)
                                break
                            else:
                                print ' ** Invalid choice (either "y" or "n")'

        # Make this variable available to Mako.
        try:
            # Include the dummy eval() statement to make sure that all that
            # can be executed by 'exec' is variable assignment: eval() will
            # raise an exception other than NameError if 'variable.destination'
            # does not resolve to a Python statement.
            #
            # Note that this still doesn't prevent malicious users from
            # executing memory bombs, or even statements like '__import__('os')
            # .remove("arbitrary_file")'.  The latter can probably be avoided
            # in part by restricting globals()['__builtins__'] to some minimal
            # list of values -- but the real, long-term solution is to
            # phase out all calls to 'eval()' and 'exec' in CuPED.  Make this
            # a priority.
            #
            # FIXME
            try:
                eval(variable.destination, globals(), variables)
            except NameError:
                pass

            exec '%s = variable.value' % \
                variable.destination in globals(), variables
        except NameError, reason:
            print "ERROR: couldn't export variable to Mako (%s)" % reason
            traceback.print_exc(file = sys.stdout)

    # Make the 'avtools' implementation available to Mako.
    variables['av'] = avtools

    # Process the templates.
    if not options.dry_run:
        for template in template_metadata.templates:
            # Make all paths absolute and create output directories as needed.
            input_file_name = template.input_file_name
            if not os.path.isabs(input_file_name):
                input_file_name = os.path.join(input_directory, input_file_name)

            output_file_name = template.output_file_name
            if not os.path.isabs(output_file_name):
                output_file_name = os.path.join \
                    (output_directory, output_file_name)

                if not os.path.exists(os.path.dirname(output_file_name)):
                    os.mkdir(os.path.dirname(output_file_name))

            # If this template should be processed, feed it into Mako and
            # store the result in the output directory under the names
            # specified in the template metadata.
            if template.should_be_processed:
                # Give Mako the template file.
                mako_template = mako.template.Template \
                    (input_encoding = 'utf-8', output_encoding = 'utf-8', \
                     filename = input_file_name)

                # Write the rendered contents of the template to the output
                # file (except in debug mode, where we render to stdout,
                # instead).
                if options.debug:
                    print mako_template.render(**variables)
                else:
                    output_file = open(output_file_name, 'w')
                    output_file.write(mako_template.render(**variables))
                    output_file.close()
            # Otherwise, just copy this file from its input location to its
            # specified output location.
            else:
                shutil.copy(input_file_name, output_file_name)

    # Now that the templates have been processed, we should be done with this
    # template metadata file.  If we've been asked to by the user, save a
    # copy of the filled-in template to disk.
    if len(options.output) > 0:
        # Update the input and output directories in the template.
        input_directory = input_directory.replace(cuped_directory, '%CuPED%')
        template_metadata.input_directory = input_directory
        output_directory = output_directory.replace(cuped_directory, '%CuPED%')
        template_metadata.output_directory = output_directory

        output_file = open(options.output[args.index(input_template)], 'w')
        output_file.write(template_metadata.__xml__())
        output_file.close()
