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
import os.path
import platform
import shutil
import sys
import tempfile
import traceback

import mako.template
from PyQt4 import QtCore, QtGui, QtWebKit

# Add the CuPED package to sys.path, if needed.
try:
    sys.path.append(os.path.abspath( \
        os.path.join(os.path.dirname(__file__), os.pardir)))
except NameError:
    pass

import cuped.avtools
import cuped.ffmpeg_qt_avtools
import cuped.template
import cuped.display

from qt.CuPEDWizardWelcome import Ui_CuPEDWizardWelcome
from qt.CuPEDWizardChooseTemplate import Ui_CuPEDWizardChooseTemplate
from qt.CuPEDWizardTemplateDetails import Ui_CuPEDWizardTemplateDetails
from qt.CuPEDWizardCustomizeVariable import Ui_CuPEDWizardCustomizeVariable
from qt.CuPEDWizardCustomizeSelection import Ui_CuPEDWizardCustomizeSelection
from qt.CuPEDWizardCustomizeTierDisplay import Ui_CuPEDWizardCustomizeTierDisplay
from qt.CuPEDWizardCustomizeTier import Ui_CuPEDWizardCustomizeTier
from qt.CuPEDWizardCustomizeTemplate import Ui_CuPEDWizardCustomizeTemplate
from qt.CuPEDWizardPreviewTemplate import Ui_CuPEDWizardPreviewTemplate
from qt.CuPEDWizardProcessTemplate import Ui_CuPEDWizardProcessTemplate
from qt.CuPEDWizardAboutCuPED import Ui_CuPEDWizardAboutCuPED
from qt.CuPEDWizardFinishedTemplate import Ui_CuPEDWizardFinishedTemplate


def warn(text = None, informativeText = None, detailedText = None):
    warning = QtGui.QMessageBox()
    warning.setIconPixmap(QtGui.QPixmap(os.path.join \
        ('bin', 'icons', 'cuped', 'Cupedplain-64x64.png')))

    if text:
        warning.setText(text)
    if informativeText:
        warning.setInformativeText(informativeText)
    if detailedText:
        warning.setDetailedText(detailedText)

    warning.exec_()

class CuPEDWizardWelcome(QtGui.QWizardPage):
    def __init__(self, parent = None, vars = {}):
        super(CuPEDWizardWelcome, self).__init__(parent)
        self.ui = Ui_CuPEDWizardWelcome()
        self.ui.setupUi(self)

        self.setTitle('Welcome to CuPED!')

class CuPEDWizardTemplateDetails(QtGui.QDialog):
    def __init__(self, parent = None):
        super(CuPEDWizardTemplateDetails, self).__init__(parent)
        self.ui = Ui_CuPEDWizardTemplateDetails()
        self.ui.setupUi(self)

        # Fully expand the last column of the 'credits' table.
        self.ui.creditsTable.horizontalHeader().setStretchLastSection(True)

        # Hide the row numbers in the 'credits' table.
        self.ui.creditsTable.verticalHeader().setVisible(False)

        # Close the window when the 'OK' button is clicked.
        self.connect(self.ui.okButton, QtCore.SIGNAL('clicked()'), self.close)

    def showTemplate(self, template):
        # Fill the basic template fields.
        self.ui.nameLineEdit.setText(template.name)
        self.ui.versionLineEdit.setText(template.version)
        self.ui.licenseLineEdit.setText(template.license)
        self.ui.descriptionTextEdit.setText(template.description)

        # Prepare the 'credits' table.
        self.ui.creditsTable.setRowCount(len(template.contributors))
        counter = 0
        for (contributor, role) in template.contributors:
            # Create widgets to represent this contributor / role in the table.
            contributorWidget = QtGui.QTableWidgetItem(contributor)
            roleWidget = QtGui.QTableWidgetItem(role)

            # Enable and make each row in the table selectable.
            flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            contributorWidget.setFlags(flags)
            roleWidget.setFlags(flags)

            # Add this contributor / role pair to the table.
            self.ui.creditsTable.setItem(counter, 0, contributorWidget)
            self.ui.creditsTable.setItem(counter, 1, roleWidget)
            counter = counter + 1

        # Adjust column widths in the 'credits' table.
        self.ui.creditsTable.resizeColumnToContents(0)

        # Show the window itself.
        self.show()

class CuPEDWizardChooseTemplate(QtGui.QWizardPage):
    # TODO: Eventually, support drag-and-drop of templates into the templates
    #       table; fix up keyboard shortcuts; allow double-clicking of
    #       templates to show details; etc.
    def __init__(self, parent = None, vars = {}):
        super(CuPEDWizardChooseTemplate, self).__init__(parent)
        self.ui = Ui_CuPEDWizardChooseTemplate()
        self.ui.setupUi(self)

        # Keep a local reference to the inter-page variables.
        self.vars = vars
        self.config = self.vars['cfg']

        # Create a template details window for use with the 'Details' button.
        self.template_details = CuPEDWizardTemplateDetails()

        # Make sure the table columns expand to fill all available space.
        self.ui.templatesTable.horizontalHeader().setStretchLastSection(True)

        # Adjust column widths.
        self.ui.templatesTable.setColumnWidth(0, 135)

        # Connect signals.
        self.connect(self.ui.templatesTable, \
            QtCore.SIGNAL('itemSelectionChanged()'), self.templateSelected)
        self.connect(self.ui.addTemplateButton, \
            QtCore.SIGNAL('clicked()'), self.addTemplateButtonClicked)
        self.connect(self.ui.removeTemplateButton, \
            QtCore.SIGNAL('clicked()'), self.removeTemplateButtonClicked)
        self.connect(self.ui.detailsButton, \
            QtCore.SIGNAL('clicked()'), self.detailsButtonClicked)

        # Set the wizard page text.
        self.setTitle('1. Choose Template')
        self.setSubTitle('Please select a CuPED template from the list ' + \
            'below, or add a template to the list using the "Add ' + \
            'template" button.  The template you select will be ' + \
            'used later to process your ELAN transcripts.')

    def initializePage(self):
        # Get the list of templates from the configuration file.
        templates = self.config.get('general', 'templates')
        if templates:
            templates = eval(templates)
            self.ui.templatesTable.setRowCount(len(templates))

            self.last_row = 0
            self.templates = []
            self.template_file_names = []

            # Add each existing template to the table.
            for template_file_name in templates:
                if os.path.isfile(template_file_name):
                    self.addTemplate(template_file_name)

        # Trigger an update of the GUI to reflect the current selection.
        # (The user could already have selected a template, and be back-
        # tracking to this item)
        self.templateSelected()

    def isComplete(self):
        return (self.vars.get('template') is not None)

    def templateSelected(self):
        # Find out what the current selection is.
        items = self.ui.templatesTable.selectedItems()

        # If the selection was cleared:
        if len(items) == 0:
            # Disable the two template-specific buttons.
            self.ui.removeTemplateButton.setEnabled(False)
            self.ui.detailsButton.setEnabled(False)

            # Remove any lingering reference to the current template.
            if 'template' in self.vars:
                del self.vars['template']

            if 'template_file_name' in self.vars:
                del self.vars['template_file_name']
        else:
            # Re-enable the template-specific buttons.
            self.ui.removeTemplateButton.setEnabled(True)
            self.ui.detailsButton.setEnabled(True)

            # Find out what row the current selection is in, get the template
            # associated with that row, and store that template in the shared
            # state under 'template' / 'template_file_name'.
            row = items[0].row()
            self.vars['template'] = self.templates[row]
            self.vars['template_file_name'] = self.template_file_names[row]

        # Let the GUI know that this page may now be complete.
        self.emit(QtCore.SIGNAL('completeChanged()'))

    def addTemplateButtonClicked(self):
        file_name = QtGui.QFileDialog.getOpenFileName(self, 'Open Template', \
            os.path.expanduser('~'), 'CuPED Templates (*.xml)')
        if file_name:
            self.addTemplate(str(file_name), add_to_config = True)

    def removeTemplateButtonClicked(self):
        # Find out what the current selection is.
        items = self.ui.templatesTable.selectedItems()
        if len(items) > 0:
            # Retrieve the object and file name for the current template, 
            # then remove any lingering references to that template.
            template = self.vars['template']
            template_file_name = self.vars['template_file_name']
            del self.vars['template']
            del self.vars['template_file_name']

            # Remove the template from our internal list(s) of templates.
            index = self.templates.index(template)
            del self.templates[index]
            del self.template_file_names[index]

            # Remove the template from the configuration file.
            self.config.set('general', 'templates', \
                '%s' % self.template_file_names)
            self.config.save()

            # Remove the template from the table.
            self.ui.templatesTable.removeRow(items[0].row())
            self.ui.templatesTable.setRowCount(len(self.templates))
            self.last_row = self.last_row - 1

    def detailsButtonClicked(self):
        # Get and show information about the current template.
        if 'template' in self.vars:
            template = self.vars['template']
            self.template_details.showTemplate(template)

    def addTemplate(self, template_file_name, add_to_config = False):
        # Try to load the template with CuPED.
        try:
            # Make sure that CuPED can parse this template.
            template = cuped.template.TemplateMetadata(template_file_name)
        except Exception, reason:
            warn("Couldn't add template!", \
                 "CuPED wasn't able to load template '%s'." % \
                  template_file_name, traceback.format_exc())
            return

        # Add this template to our internal list(s) of templates.
        self.templates.append(template)
        self.template_file_names.append(template_file_name)

        # Expand the input and output directories within this template.
        cuped_directory = os.path.abspath(os.curdir)
        if os.altsep:
            cuped_directory = cuped_directory.replace(os.sep, os.altsep)

        template.input_directory = template.input_directory.replace \
            ('%CuPED%', cuped_directory)
        template.output_directory = template.output_directory.replace \
            ('%CuPED%', cuped_directory)

        # If asked to, save a reference to this template in the CuPED
        # configuration file.
        if add_to_config:
            self.config.set('general', 'templates', \
                '%s' % self.template_file_names)
            self.config.save()

        # Create widgets to represent this template in the table.
        nameWidget = QtGui.QTableWidgetItem(template.name)
        descriptionWidget = QtGui.QTableWidgetItem(template.description)

        # Enable each of the rows in the table and make each row
        # selectable.
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        nameWidget.setFlags(flags)
        descriptionWidget.setFlags(flags)

        # Adjust the font size on OSX.
        if platform.uname()[0] == 'Darwin':
            font = nameWidget.font()
            font.setPointSize(font.pointSize() * 0.8)
            nameWidget.setFont(font)
            descriptionWidget.setFont(font)

        # Add the widgets to the table.
        self.ui.templatesTable.setRowCount(len(self.templates))
        self.ui.templatesTable.setItem(self.last_row, 0, nameWidget)
        self.ui.templatesTable.setItem(self.last_row, 1, descriptionWidget)
        self.last_row = self.last_row + 1

class CuPEDWizardCustomizeVariable(QtGui.QWizardPage):
    def __init__(self, parent = None, variable = None, variables = []):
        super(CuPEDWizardCustomizeVariable, self).__init__(parent)
        self.ui = Ui_CuPEDWizardCustomizeVariable()
        self.ui.setupUi(self)

        # Save a copy of the variable to be customized and the set of all the
        # variables being customized
        self.variable = variable
        self.variables = variables

        # Get the maximum number of items that the user can select for this
        # variable.  (This defaults to a single item, if nothing else is
        # given)
        self.max_selection = 1
        if 'maxSelection' in variable.options:
            self.max_selection = int(variable.options['maxSelection'])

        # Set up the default behaviour of this widget.
        self.connect(self.ui.settingsList, \
            QtCore.SIGNAL('itemSelectionChanged()'), self.updateButtons)
        self.connect(self.ui.upButton, \
            QtCore.SIGNAL('clicked()'), self.upButtonClicked)
        self.connect(self.ui.downButton, \
            QtCore.SIGNAL('clicked()'), self.downButtonClicked)
        self.connect(self.ui.addButton, \
            QtCore.SIGNAL('clicked()'), self.addButtonClicked)
        self.connect(self.ui.editButton, \
            QtCore.SIGNAL('clicked()'), self.editButtonClicked)
        self.connect(self.ui.removeButton, \
            QtCore.SIGNAL('clicked()'), self.removeButtonClicked)

    def initialize(self):
        # Create a list entry for each of the choices for values of this
        # variable.
        self.ui.settingsList.clear()
        for choice in self.variable.choice:
            item = QtGui.QListWidgetItem(choice, self.ui.settingsList)

        # Make sure all of the buttons are in the right state.
        self.updateButtons()

        # Let all listeners know that the user's choices have changed.
        self.emit(QtCore.SIGNAL('updatedChoices'), self)

    def parentChanged(self):
        self.variable.choice = []
        self.initialize()

    def updateButtons(self):
        # Enable the up and down buttons only when there are items in the list.
        count = self.ui.settingsList.count()
        self.ui.upButton.setEnabled(count > 1)
        self.ui.downButton.setEnabled(count > 1)

        # If there are already 'maxSelection' items in the list, don't allow
        # the user to add more.
        self.ui.addButton.setEnabled(count < self.max_selection)

        # If there are no selections, disable the 'edit' and 'remove' buttons.
        count_selections = len(self.ui.settingsList.selectedItems())
        self.ui.editButton.setEnabled(count_selections > 0)
        self.ui.removeButton.setEnabled(count_selections > 0)

    def upButtonClicked(self):
        # Get the item that the user has selected.
        selection = self.ui.settingsList.selectedItems()
        if len(selection) == 0:
            return

        # Get the list widget and its associated item.
        listItem = selection[0]
        index = self.ui.settingsList.row(listItem)
        choice = self.variable.choice[index]

        # If we aren't already at the top of the list, move the item up one
        # spot.
        if index > 0:
            # Remove the old item.
            self.ui.settingsList.takeItem(index)
            del self.variable.choice[index]

            # Re-insert that item one position earlier.
            self.ui.settingsList.insertItem(index - 1, listItem)
            self.variable.choice.insert(index - 1, choice)

            # Make the selection follow the moved item.
            self.ui.settingsList.setItemSelected(listItem, True)

            # Let all listeners know that the user's choices have changed.
            self.emit(QtCore.SIGNAL('updatedChoices'), self)

    def downButtonClicked(self):
        # Get the item that the user has selected.
        selection = self.ui.settingsList.selectedItems()
        if len(selection) == 0:
            return

        # Get the list widget and its associated item.
        listItem = selection[0]
        index = self.ui.settingsList.row(listItem)
        choice = self.variable.choice[index]

        # If we aren't already at the bottom of the list, move the item down
        # one spot.
        if index < len(self.variable.choice) - 1:
            # Remove the old item.
            self.ui.settingsList.takeItem(index)
            del self.variable.choice[index]

            # Re-insert that item one position later.
            self.ui.settingsList.insertItem(index + 1, listItem)
            self.variable.choice.insert(index + 1, choice)

            # Make the selection follow the moved item.
            self.ui.settingsList.setItemSelected(listItem, True)

            # Let all listeners know that the user's choices have changed.
            self.emit(QtCore.SIGNAL('updatedChoices'), self)

    def addButtonClicked(self):
        # Get a new choice of values for this variable from the user.
        item = self.add()
        if item is None:
            return

        # Create a display widget for this item.
        listItem = QtGui.QListWidgetItem()
        listItem.setText(self.str(item))

        # Insert the new item into the settings list.  (If the user has
        # selected one particular item in the list, insert this new item
        # into the position immediately after that one)
        selection = self.ui.settingsList.selectedItems()
        if len(selection) > 0:
            row = self.ui.settingsList.row(selection[len(selection) - 1])
            self.ui.settingsList.insertItem(row, listItem)
            self.variable.choice.insert(row, item)
        else:
            self.ui.settingsList.addItem(listItem)
            self.variable.choice.append(item)

        # Update which buttons are activated.
        self.updateButtons()

        # Let all listeners know that the user's choices have changed.
        self.emit(QtCore.SIGNAL('updatedChoices'), self)

    def editButtonClicked(self):
        # Get the item that the user has selected.
        selection = self.ui.settingsList.selectedItems()
        if len(selection) == 0:
            return

        # Get the item that the user has selected.
        listItem = selection[0]
        index = self.ui.settingsList.row(listItem)
        item = self.variable.choice[index]

        # Ask the user to edit this item.  If any changes are made, update
        # both the display and our internal list of items.
        newItem = self.edit(item)
        if newItem is not None:
            listItem.setText(self.str(newItem))
            self.variable.choice[index] = newItem

            # Let all listeners know that the user's choices have changed.
            self.emit(QtCore.SIGNAL('updatedChoices'), self)

    def removeButtonClicked(self):
        # Get the item that the user has selected.
        selection = self.ui.settingsList.selectedItems()
        if len(selection) == 0:
            return

        # Remove the item that the user has selected from the display and
        # from our internal list of items.
        row = self.ui.settingsList.row(selection[0])
        del self.variable.choice[row]
        self.ui.settingsList.takeItem(row)

        # Update which buttons are activated.
        self.updateButtons()

        # Let all listeners know that the user's choices have changed.
        self.emit(QtCore.SIGNAL('updatedChoices'), self)

    def add(self):
        """Returns an item to be added to the list."""
        raise NotImplementedError

    def edit(self, item):
        """Returns an item to replace the given item in the list."""
        raise NotImplementedError

    def str(self, item):
        """Returns a string representation of the given item."""
        raise NotImplementedError

class CuPEDWizardCustomizeString(CuPEDWizardCustomizeVariable):
    def __init__(self, parent = None, variable = None, variables = []):
        super(CuPEDWizardCustomizeString, self).__init__(parent, variable, \
            variables)

    def add(self):
        # Ask the user to provide a new choice of values for the selected
        # variable.
        text, ok = QtGui.QInputDialog.getText(self, 'CuPED - Add string', \
            'Enter a value for "%s":' % self.variable.name)

        # If the user provided a valid value, return it in string form.
        if ok and text is not None:
            # Enforce minimum string lengths.
            if 'minLength' in self.variable.options:
                minLength = int(self.variable.options['minLength'])
                if len(text) < minLength:
                    warn("Can't add string!", \
                         "The string must be at least %d characters long" % \
                          minLength)
                    return None

            # Enforce maximum string lengths.
            if 'maxLength' in self.variable.options:
                maxLength = int(self.variable.options['maxLength'])
                if len(text) > maxLength:
                    warn("Can't add string!", \
                         "The string must be no more than %d characters long" \
                          % maxLength)
                    return None

            return str(text)

        # Otherwise, return None.
        return None

    def edit(self, item):
        # Ask the user to edit the given string, then return it (or None if
        # the edit was cancelled)
        text, ok = QtGui.QInputDialog.getText(self, 'CuPED - Edit string', \
            'Enter a new value for "%s":' % self.variable.name, \
             QtGui.QLineEdit.Normal, item)

        # If the user provided a valid value, return it in string form.
        if ok and text is not None:
            # Enforce minimum string lengths.
            if 'minLength' in self.variable.options:
                minLength = int(self.variable.options['minLength'])
                if len(text) < minLength:
                    warn("Can't edit string!", \
                         "The string must be at least %d characters long" % \
                          minLength)
                    return None

            # Enforce maximum string lengths.
            if 'maxLength' in self.variable.options:
                maxLength = int(self.variable.options['maxLength'])
                if len(text) > maxLength:
                    warn("Can't edit string!", \
                         "The string must be no more than %d characters long" \
                          % maxLength)
                    return None

            return str(text)

        # Otherwise, return None.
        return None

    def str(self, item):
        # Strings are printable as-is!
        return item

class CuPEDWizardCustomizeDirectory(CuPEDWizardCustomizeVariable):
    def __init__(self, parent = None, variable = None, variables = []):
        super(CuPEDWizardCustomizeDirectory, self).__init__(parent, \
            variable, variables)

    def add(self):
        # Prompt the user to select a directory.
        return self._getDirectory(QtGui.QDesktopServices.storageLocation \
            (QtGui.QDesktopServices.DesktopLocation))

    def edit(self, item):
        # Prompt the user to change their choice of directories, defaulting to
        # the given directory (if it can be found).
        if os.path.isdir(item):
            return self._getDirectory(item)

        return self.add()

    def str(self, item):
        # Directory names can be displayed as-is.
        return item

    def _getDirectory(self, item):
        q_dirname = QtGui.QFileDialog.getExistingDirectory(self, \
            'CuPED - Open directory', item)
        if q_dirname:
            return str(q_dirname)

        return None

class CuPEDWizardCustomizeFile(CuPEDWizardCustomizeVariable):
    def __init__(self, parent = None, variable = None, variables = []):
        super(CuPEDWizardCustomizeFile, self).__init__(parent, \
            variable, variables)

    def add(self):
        # Prompt the user to select a file.
        return self._getFile(QtGui.QDesktopServices.storageLocation \
            (QtGui.QDesktopServices.DesktopLocation))

    def edit(self, item):
        # Prompt the user to select a new file, defaulting to the given file
        # (if it can be found).
        if os.path.isfile(item):
            return self._getFile(item)

        return self.add()

    def str(self, item):
        # File names can be displayed as-is.
        return item

    def _getFile(self, oldFile):
        filter = 'All files (*)'
        if 'fileType' in self.variable.options:
            fileType = self.variable.options['fileType']
# TODO: where to get these filters from, in a less hackish fashion?  (From
#       the current instance of 'avtools', I suppose.  Fix this!)
            if fileType == 'image':
                filter = 'Image files (*.png *.jpg *.gif)'
            elif fileType == 'audio':
                filter = 'Audio files (*.wav *.aif *.aiff *.mp3 *.m4a)'
            elif fileType == 'video':
                filter = 'Video files (*.mpg *.mp2 *.mp4 *.m2v *.mov *.avi)'
            elif fileType == 'av':
                filter = 'Audio and video files ' + \
                    '(*.wav *.aif *.aiff *.mp3 *.m4a ' + \
                    '*.mpg *.mp2 *.mp4 *.m2v *.mov *.avi)'
            elif fileType == 'transcript':
                filter = 'Transcript files (*.eaf)'

        q_filename = QtGui.QFileDialog.getOpenFileName(self, \
            'CuPED - Open file', oldFile, filter)
        if q_filename:
            return str(q_filename)

        return None

class CuPEDWizardCustomizeTranscript(CuPEDWizardCustomizeVariable):
    def __init__(self, parent = None, variable = None, variables = []):
        super(CuPEDWizardCustomizeTranscript, self).__init__(parent, \
            variable, variables)

    def add(self):
        # Prompt the user to select a transcript.
        return self._getTranscript(QtGui.QDesktopServices.storageLocation \
            (QtGui.QDesktopServices.DocumentsLocation))

    def edit(self, item):
        # Prompt the user to select a different transcript, defaulting to the
        # given transcript (if it's available).
        if os.path.isfile(item):
            return self._getTranscript(item)

        return self.add()

    def str(self, item):
        # Return the file name of the transcript as its display name.
        return item

    def _getTranscript(self, item):
# TODO: where to get this filter from, in a less hackish fashion?  (From
#       the current instance of 'avtools', I suppose.  Fix this!)
        q_transcript = QtGui.QFileDialog.getOpenFileName(self, \
            'CuPED - Open transcript', item, 'All transcripts (*.eaf)')
        if q_transcript:
            return str(q_transcript)

        return None

class CuPEDWizardCustomizeColour(CuPEDWizardCustomizeVariable):
    def __init__(self, parent = None, variable = None, variables = []):
        super(CuPEDWizardCustomizeColour, self).__init__(parent, \
            variable, variables)

    def add(self):
        # Prompt the user to select a colour.
        qc = QtGui.QColorDialog.getColor(QtCore.Qt.white, self)
        if qc.isValid():
            return "#%02x%02x%02x" % (qc.red(), qc.green(), qc.blue())

        return None

    def edit(self, item):
        # Convert the given colour string into a CuPED colour.
        colour = cuped.display.CuPEDColour(item)

        # Prompt the user to edit an existing colour.
        old = QtGui.QColor(colour.red, colour.green, colour.blue)
        qc = QtGui.QColorDialog.getColor(old, self)
        if qc.isValid():
            return "#%02x%02x%02x" % (qc.red(), qc.green(), qc.blue())

        return None

    def str(self, item):
        # For now, colours can be printed as hexadecimal values.
        # TODO: improve this later on! (maybe this method could return
        # listwidgets, instead?)
        return str(item)

class CuPEDWizardCustomizeFont(CuPEDWizardCustomizeVariable):
    def __init__(self, parent = None, variable = None, variables = []):
        super(CuPEDWizardCustomizeFont, self).__init__(parent, \
            variable, variables)

    def add(self):
        # Prompt the user to select a font.
        qfont, ok = QtGui.QFontDialog.getFont(self)
        if ok:
            return self.str(self._qfont_to_cuped_font(qfont))

        return None

    def edit(self, item):
        # Prompt the user to edit an existing font.
        old = self._cuped_font_to_qfont(cuped.display.CuPEDFont(item))
        qfont, ok = QtGui.QFontDialog.getFont(old)
        if ok:
            return self.str(self._qfont_to_cuped_font(qfont))

        return None

    def str(self, item):
        return str(item)

    def _qfont_to_cuped_font(self, qfont):
        font = cuped.display.CuPEDFont()
        font.font_name = str(qfont.family())
        font.font_size = qfont.pointSize()
        font.is_bold = qfont.bold()
        font.is_italic = qfont.italic()
        font.is_underline = qfont.underline()
        font.is_strike_through = qfont.strikeOut()
        font.is_small_caps = (qfont.capitalization() == QtGui.QFont.SmallCaps)
        return font

    def _cuped_font_to_qfont(self, font):
        qfont = QtGui.QFont()
        qfont.setFamily(font.font_name)
        qfont.setPointSize(font.font_size)
        qfont.setBold(font.is_bold)
        qfont.setItalic(font.is_italic)
        qfont.setUnderline(font.is_underline)
        qfont.setStrikeOut(font.is_strike_through)
        if font.is_small_caps:
            qfont.setCapitalization(QtGui.QFont.SmallCaps)

        return qfont

class CuPEDWizardCustomizeSelection(QtGui.QWizardPage):
    def __init__(self, parent = None, variable = None, variables = [], \
                 do_layout = True):
        # By default, initialize the layout of this widget here.  (Disabling
        # this allows some subclasses to inherit behaviour, but not all of
        # the layout)
        if do_layout:
            super(CuPEDWizardCustomizeSelection, self).__init__(parent)
            self.ui = Ui_CuPEDWizardCustomizeSelection()
            self.ui.setupUi(self)

        # Save a copy of the variable to be customized and the set of all the
        # variables being customized.
        self.variable = variable
        self.variables = variables

        # Get the maximum number of items that the user can select for this
        # variable.  (This defaults to a single item, if nothing else is
        # given)
        self.max_selection = 1
        if 'maxSelection' is variable.options:
            self.max_selection = int(variable.options['maxSelection'])

        # Set up the default behaviour of this widget.
        self.connect(self.ui.settingsList, \
            QtCore.SIGNAL('itemSelectionChanged()'), self.updateButtons)
        self.connect(self.ui.settingsList, \
            QtCore.SIGNAL('itemChanged(QListWidgetItem*)'), self.itemChanged)
        self.connect(self.ui.upButton, \
            QtCore.SIGNAL('clicked()'), self.upButtonClicked)
        self.connect(self.ui.downButton, \
            QtCore.SIGNAL('clicked()'), self.downButtonClicked)

    def initialize(self):
        # Clear the old list of available options.
        self.ui.settingsList.clear()
        self.possibility_names = []
        self.possibility_values = []

        # Temporarily disconnect the 'itemChanged' signal while we're building
        # the list.
        self.disconnect(self.ui.settingsList, \
            QtCore.SIGNAL('itemChanged(QListWidgetItem*)'), self.itemChanged)

        # Get the list of possible choices for this variable.
        possibilities = None
        try:
            vmap = dict([(v.destination, v.value) for v in self.variables])
            possibilities = self.variable.get_possible_choices(vmap)
        except Exception:
            pass

        # If there are possible values for this variable (which may not be the
        # case -- if it depends on another variable, its 'range' may not be
        # eval()uable, causing 'variable.get_possible_choices()' to raise an
        # exception), process them.
        if possibilities:
            # Turn each possibility into a separate list item.
            for (name, description, value) in possibilities:
                item = QtGui.QListWidgetItem(name, self.ui.settingsList)
                item.setToolTip(description)
                self.possibility_names.append(name)
                self.possibility_values.append(value)

            # Check each entry that has been chosen by the user.
            for index in range(0, len(self.possibility_names)):
                item = self.ui.settingsList.item(index)
                name = self.possibility_names[index]
                if name in self.variable.choice:
                    item.setCheckState(QtCore.Qt.Checked)
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)

        # Reconnect the 'itemChanged' signal, now that the list is ready.
        self.connect(self.ui.settingsList, \
            QtCore.SIGNAL('itemChanged(QListWidgetItem*)'), self.itemChanged)

        # Let all listeners know that the user's choices have changed.
        self.emit(QtCore.SIGNAL('updatedChoices'), self)

    def parentChanged(self):
        self.variable.choice = []
        self.initialize()
        self.updateButtons()

    def itemChanged(self, widget):
        # Update the choices of values for this variable.
        choices = []
        for index in range(0, self.ui.settingsList.count()):
            child = self.ui.settingsList.item(index)
            if child.checkState() == QtCore.Qt.Checked:
                choices.append(str(child.text()))

        self.variable.choice = choices

        # Update button states to reflect the current values.
        self.updateButtons()

        # Let all listeners know that the user's choices have changed.
        self.emit(QtCore.SIGNAL('updatedChoices'), self)

    def updateButtons(self):
        # Enable the up and down buttons only when more than one item can be
        # selected in the list.
        enable_buttons = ((self.ui.settingsList.count() > 1) and \
            (self.max_selection > 1))
        self.ui.upButton.setEnabled(enable_buttons)
        self.ui.downButton.setEnabled(enable_buttons)

        # Find out how many items have been selected by the user.
        count = 0
        for index in range(0, self.ui.settingsList.count()):
            child = self.ui.settingsList.item(index)
            if child.checkState() == QtCore.Qt.Checked:
                count = count + 1

        # Temporarily disconnect the list-related signals.
        self.disconnect(self.ui.settingsList, \
            QtCore.SIGNAL('itemSelectionChanged()'), self.updateButtons)
        self.disconnect(self.ui.settingsList, \
            QtCore.SIGNAL('itemChanged(QListWidgetItem*)'), self.itemChanged)

        # Enforce max selection.
        have_max_selection = (count >= self.max_selection)
        for index in range(0, self.ui.settingsList.count()):
            child = self.ui.settingsList.item(index)
            if child.checkState() != QtCore.Qt.Checked:
                if have_max_selection:
                    child.setFlags(QtCore.Qt.NoItemFlags)
                else:
                    child.setFlags(QtCore.Qt.ItemIsUserCheckable | \
                        QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        # Reconnect the list-related signals.
        self.connect(self.ui.settingsList, \
            QtCore.SIGNAL('itemSelectionChanged()'), self.updateButtons)
        self.connect(self.ui.settingsList, \
            QtCore.SIGNAL('itemChanged(QListWidgetItem*)'), self.itemChanged)

    def upButtonClicked(self):
        # Get the item that the user has selected.
        selection = self.ui.settingsList.selectedItems()
        if len(selection) == 0:
            return

        # Get the selected list widget and its position in the list.
        item = selection[0]
        item_index = self.ui.settingsList.row(item)

        # If this widget isn't already at the top of the list, move it up
        # one position and have the selection follow it there.  (This change
        # is entirely superficial, but it doesn't hurt to allow it)
        if item_index > 0:
            self.ui.settingsList.takeItem(item_index)
            self.ui.settingsList.insertItem(item_index - 1, item)
            self.ui.settingsList.setItemSelected(item, True)

        # Get the associated choice of values.
        name = listItem.text()
        choice_index = self.variable.choice.index(name)
        choice = self.variable.choice[choice_index]

        # If this isn't already the top choice for a value for this variable,
        # move it up one position in the list of choices for values.
        if choice_index > 0:
            del self.variable.choice[choice_index]
            self.variable.choice.insert(choice_index - 1, choice)

            # Let all listeners know that the user's choices have changed.
            self.emit(QtCore.SIGNAL('updatedChoices'), self)

    def downButtonClicked(self):
        # Get the item that the user has selected.
        selection = self.ui.settingsList.selectedItems()
        if len(selection) == 0:
            return

        # Get the selected list widget and its position in the list.
        item = selection[0]
        item_index = self.ui.settingsList.row(item)

        # If this widget isn't already at the top of the list, move it up
        # one position and have the selection follow it there.  (This change
        # is entirely superficial, but it doesn't hurt to allow it)
        if item_index < len(self.ui.settingsList.count()):
            self.ui.settingsList.takeItem(item_index)
            self.ui.settingsList.insertItem(item_index + 1, item)
            self.ui.settingsList.setItemSelected(item, True)

        # Get the associated choice of values.
        name = listItem.text()
        choice_index = self.variable.choice.index(name)
        choice = self.variable.choice[choice_index]

        # Move this choice one position down in the list of choices of values
        # for this variable.
        if choice_index < len(self.variable.choice):
            del self.variable.choice[choice_index]
            self.variable.choice.insert(choice_index + 1, choice)

            # Let all listeners know that the user's choices have changed.
            self.emit(QtCore.SIGNAL('updatedChoices'), self)

class CuPEDWizardCustomizeTierDisplay(QtGui.QDialog):
    def __init__(self, parent = None):
        super(CuPEDWizardCustomizeTierDisplay, self).__init__(parent)
        self.ui = Ui_CuPEDWizardCustomizeTierDisplay()
        self.ui.setupUi(self)

        self.connect(self.ui.okButton, \
            QtCore.SIGNAL('clicked()'), self.okButtonClicked)
        self.connect(self.ui.foregroundColourButton, \
            QtCore.SIGNAL('clicked()'), self.foregroundColourButtonClicked)
        self.connect(self.ui.backgroundColourButton, \
            QtCore.SIGNAL('clicked()'), self.backgroundColourButtonClicked)
        self.connect(self.ui.tierDisplayGroupBox, \
            QtCore.SIGNAL('clicked(bool)'), self.groupBoxChecked)

    def customizeTierDisplay(self, tier_name, variable, variables, \
        display_variables):
        # Save local copies of the given variables.
        self.tier_name = tier_name
        self.variable = variable
        self.variables = variables
        self.display_variables = display_variables

        # Set up variables for the font, foreground and background colours,
        # and visibility of this tier.
        self.font_variable = cuped.template.TemplateMetadataVariable()
        self.font_variable.name = '"%s" tier font(s)' % tier_name
        self.font_variable.description = 'Font(s) for tier "%s"' % tier_name
        self.font_variable.type = 'font'
        self.font_variable.choice = []
        self.font_variable.destination = 'filter(lambda x: ' + \
            'x.name == "%s", transcript[0].tiers)[0].fonts' % tier_name
        self.font_variable.options['tierDisplayVariable'] = tier_name
        self.font_variable.options['maxSelection'] = '20'   # HACK
        self.font_variable.dependency = variable.dependency

        self.background_colour_variable = \
            cuped.template.TemplateMetadataVariable()
        self.background_colour_variable.name = \
            '"%s" tier background colour' % tier_name
        self.background_colour_variable.description = \
            'Background colour for tier "%s"' % tier_name
        self.background_colour_variable.type = 'colour'
        self.background_colour_variable.choice = None
# FIXME: 'transcript[0].tiers' should be 'variable.range', instead, I think
#        (or somehow referring back to the transcript whose tiers this depends
#         on; figure this out, and fix in several sections below!)
        self.background_colour_variable.destination = 'filter(lambda x: ' + \
            'x.name == "%s", transcript[0].tiers)[0].background_colour' % \
             tier_name
        self.background_colour_variable.options['tierDisplayVariable'] = \
            tier_name
        self.background_colour_variable.dependency = variable.dependency

        self.foreground_colour_variable = \
            cuped.template.TemplateMetadataVariable()
        self.foreground_colour_variable.name = \
            '"%s" tier foreground colour' % tier_name
        self.foreground_colour_variable.description = \
            'Foreground colour for tier "%s"' % tier_name
        self.foreground_colour_variable.type = 'colour'
        self.foreground_colour_variable.choice = None
        self.foreground_colour_variable.destination = 'filter(lambda x: ' + \
            'x.name == "%s", transcript[0].tiers)[0].foreground_colour' % \
             tier_name
        self.foreground_colour_variable.options['tierDisplayVariable'] = \
            tier_name
        self.foreground_colour_variable.dependency = variable.dependency

        self.visibility_variable = cuped.template.TemplateMetadataVariable()
        self.visibility_variable.name = '"%s" tier visibility' % tier_name
        self.visibility_variable.description = \
            'Is tier "%s" visible?' % tier_name
        self.visibility_variable.type = 'selection'
        self.visibility_variable.choice = ['Yes']
        self.visibility_variable.destination = 'filter(lambda x: x.name ' + \
            '== "%s", transcript[0].tiers)[0].is_visible' % tier_name
        self.visibility_variable.range = \
            "[('Yes', 'Yes, this tier is visible', True)," + \
            " ('No', 'No, this tier is not visible', False)]"
        self.visibility_variable.options['tierDisplayVariable'] = tier_name
        self.visibility_variable.dependency = variable.dependency

        # Go through and find all of the display variables associated with
        # this tier.  Where matches are found, assign the user's previous
        # choice of values to the appropriate new display variables.
        for (display_tier_name, display_variable) in display_variables:
            if display_tier_name == tier_name:
                if display_variable.type == 'font':
                    self.font_variable.choice = display_variable.choice
                elif display_variable.type == 'selection':
                    self.visibility_variable.choice = display_variable.choice
                elif display_variable.type == 'colour' or \
                     display_variable.type == 'color':
                    # HACK
                    if display_variable.destination.endswith \
                        ('background_colour'):
                        self.background_colour_variable.choice = \
                            display_variable.choice
                    else:
                        self.foreground_colour_variable.choice = \
                            display_variable.choice

        # Populate existing widgets to display these variables.
        self.ui.tierDisplayGroupBox.setChecked \
            (self.visibility_variable.choice != ['No'])

        if self.foreground_colour_variable.choice:
            self.ui.foregroundColourLabel.setText \
                (self.foreground_colour_variable.choice[0])
        else:
            self.ui.foregroundColourLabel.setText('(none)')

        if self.background_colour_variable.choice:
            self.ui.backgroundColourLabel.setText \
                (self.background_colour_variable.choice[0])
        else:
            self.ui.backgroundColourLabel.setText('(none)')

        # Replace the placeholder widget with a font selection box.
        layout = self.ui.tierDisplayGroupBox.layout()
        for child in self.ui.tierDisplayGroupBox.children():
            if child.objectName() == 'dummyWidget':
                child.setVisible(False)
                self.ui.tierDisplayGroupBox.layout().removeWidget(child)

                self.fonts = CuPEDWizardCustomizeFont \
                    (variable = self.font_variable, variables = variables)
                self.fonts.initialize()
                self.fonts.setObjectName('dummyWidget')
                self.fonts.setMinimumWidth(child.minimumWidth())
                self.fonts.setMinimumHeight(child.minimumHeight())
                self.fonts.setSizePolicy(child.sizePolicy())
                self.ui.tierDisplayGroupBox.layout().addWidget(self.fonts, \
                    0, 0, 1, 3)
                self.fonts.setVisible(True)
                break

        # Display the window to the user.
        self.exec_()

    def promptColour(self, variable):
        # Either begin editing the existing colour, or default to white.
        if variable.choice:
            colour = cuped.display.CuPEDColour(variable.choice[0])
        else:
            colour = cuped.display.CuPEDColour('#ffffff')

        # Prompt the user to edit the given colour.
        old = QtGui.QColor(colour.red, colour.green, colour.blue)
        qc = QtGui.QColorDialog.getColor(old, self)
        if qc.isValid():
            variable.choice = ["#%02x%02x%02x" % \
                (qc.red(), qc.green(), qc.blue())]
        else:
            variable.choice = []

        return variable.choice

    def foregroundColourButtonClicked(self):
        if self.promptColour(self.foreground_colour_variable):
            self.ui.foregroundColourLabel.setText \
                (self.foreground_colour_variable.choice[0])
        else:
            self.ui.foregroundColourLabel.setText('(none)')

    def backgroundColourButtonClicked(self):
        if self.promptColour(self.background_colour_variable):
            self.ui.backgroundColourLabel.setText \
                (self.background_colour_variable.choice[0])
        else:
            self.ui.backgroundColourLabel.setText('(none)')

    def groupBoxChecked(self, checked = False):
        # Assign a value to the visibility variable to reflect the current
        # state of the checkbox.
        choice = 'No'
        if checked:
            choice = 'Yes'

        self.visibility_variable.choice = [choice]

    def okButtonClicked(self):
        # Remove the old display variables from the list of display variables
        # and from the template itself.
        for (display_tier_name, display_variable) in self.display_variables:
            if display_tier_name == self.tier_name:
                self.display_variables.remove \
                    ((display_tier_name, display_variable))
                del self.variables[self.variables.index(display_variable)]

        # Reset the display attributes for this tier.
        self.variable.foreground_colour = None
        self.variable.background_colour = None
        self.variable.fonts = []
        self.is_visible = True
        vmap = dict((v.destination, v.value) for v in self.variables)

        # Add the new display variables to the template and to the list of
        # display variables, and update the tier's own display attributes.
        if self.font_variable.choice:
            self.variables.append(self.font_variable)
            self.display_variables.append((self.tier_name, self.font_variable))
            self.font_variable.assign_choices(self.font_variable.choice, vmap)

        if self.background_colour_variable.choice:
            self.variables.append(self.background_colour_variable)
            self.display_variables.append((self.tier_name, \
                self.background_colour_variable))
            self.background_colour_variable.assign_choices \
                (self.background_colour_variable.choice, vmap, unlist = True)

        if self.foreground_colour_variable.choice:
            self.variables.append(self.foreground_colour_variable)
            self.display_variables.append((self.tier_name, \
                self.foreground_colour_variable))
            self.foreground_colour_variable.assign_choices \
                (self.foreground_colour_variable.choice, vmap, unlist = True)

        if self.visibility_variable.choice:
            self.variables.append(self.visibility_variable)
            self.display_variables.append((self.tier_name, \
                self.visibility_variable))
            self.visibility_variable.assign_choices \
                (self.visibility_variable.choice, vmap, unlist = True)

        # Hide this window.
        self.close()

class CuPEDWizardCustomizeTier(CuPEDWizardCustomizeSelection):
    def __init__(self, parent = None, variable = None, variables = [], \
                 display_variables = []):
        super(CuPEDWizardCustomizeSelection, self).__init__(parent)
        self.ui = Ui_CuPEDWizardCustomizeTier()
        self.ui.setupUi(self)
        super(CuPEDWizardCustomizeTier, self).__init__(parent, \
            variable, variables, False)

        # Keep a local reference to the list of (tier_name, display_variable)
        # tuples provided to this method.
        self.display_variables = display_variables

        # Create and hide a widget for displaying tier display options.
        self.tier_display = CuPEDWizardCustomizeTierDisplay()
        self.tier_display.setVisible(False)

        # Connect the extra buttons.
        self.connect(self.ui.optionsButton, \
            QtCore.SIGNAL('clicked()'), self.optionsButtonClicked)
        self.connect(self.ui.clearButton, \
            QtCore.SIGNAL('clicked()'), self.clearButtonClicked)

    def setVisible(self, visible):
        CuPEDWizardCustomizeSelection.setVisible(self, visible)
        self.updateListFormatting()

    def updateButtons(self):
        # If the user has made a selection, enable the 'options' and 'clear'
        # buttons.
        selections = self.ui.settingsList.selectedItems()
        enable_buttons = (len(selections) > 0)
        self.ui.optionsButton.setEnabled(enable_buttons)
        self.ui.clearButton.setEnabled(enable_buttons)

        # Only enable the 'clear' button if there is at least one display
        # variable associated with the selected tier.
        if enable_buttons:
            selection_name = selections[0].text()
            tier_names = [name for (name, var) in self.display_variables]
            self.ui.clearButton.setEnabled(selection_name in tier_names)

        # Finally, do the default behaviour for when buttons are clicked.
        super(CuPEDWizardCustomizeTier, self).updateButtons()

    def updateListFormatting(self):
        # Print in bold each row that has at least one display variable
        # associated with it.
        tier_names = [x for (x, y) in self.display_variables]
        for row in range(0, self.ui.settingsList.count()):
            tier_widget = self.ui.settingsList.item(row)
            tier_font = tier_widget.font()
            tier_font.setBold(str(tier_widget.text()) in tier_names)
            tier_widget.setFont(tier_font)

    def optionsButtonClicked(self):
        # Get the name of the tier currently selected.
        tier_name = self.ui.settingsList.selectedItems()[0].text()

        # Prompt the user to add or edit the display options for this tier.
        # (This takes care of adding and removing variables from the list of
        #  display variables and from the template transparently)
        self.tier_display.customizeTierDisplay(str(tier_name), self.variable, \
            self.variables, self.display_variables)

        # Update the formatting of items in the list.
        self.updateListFormatting()

    def clearButtonClicked(self):
        # Clear and remove all of the display variables associated with the
        # selected item.

        # Get the current selection.
        item = self.ui.settingsList.selectedItems()[0]
        row = self.ui.settingsList.row(item)
        name = item.text()

        # Run through all of the display variables and remove any that refer
        # to the selected tier.  (These need to be removed both from the list
        # of display variables and from the larger list of variables that are
        # present in the template)
        pos = []
        for (tier_name, display_variable) in self.display_variables:
            if tier_name == name:
                pos.insert(0, self.display_variables.index \
                    ((tier_name, display_variable)))
                self.variables.remove(display_variable)

        for i in pos:
            del self.display_variables[i]

# So, for some reason, fonts aren't being saved as part of user selections
# (or at least not font names).  Figure out why this is!
#
# Also, when you select an item, everything else in the list seems to
# disappear; figure out what this is all about (probably changes to how
# things are initialized, I'd guess, but it could be something else, too).
#
# (At least the clear button is fixed now...)
#
# FROMHERE

        # Now clear the display attributes of the tier itself.
        tiers = filter(lambda x: x.name == self.variable.dependency, \
            self.variables)[0].value[0].tiers
        tier = filter(lambda y: y.name == name, tiers)[0]
        tier.fonts = []
        tier.foreground_colour = None
        tier.background_colour = None
        tier.is_visible = True

        # Update the formatting of items in the list.
        self.updateListFormatting()

class CuPEDWizardCustomizeTemplate(QtGui.QWizardPage):
    def __init__(self, parent = None, vars = {}):
        super(CuPEDWizardCustomizeTemplate, self).__init__(parent)
        self.ui = Ui_CuPEDWizardCustomizeTemplate()
        self.ui.setupUi(self)

        # Create icons representing possible variable states.
        self.optionalCompleteIcon = QtGui.QIcon( \
            os.path.join('bin', 'icons', 'circular', 'heart_green.png'))
        self.optionalIncompleteIcon = QtGui.QIcon( \
            os.path.join('bin', 'icons', 'circular', 'heart_blue.png'))
        self.requiredCompleteIcon = QtGui.QIcon( \
            os.path.join('bin', 'icons', 'circular', 'star_green.png'))
        self.requiredIncompleteIcon = QtGui.QIcon( \
            os.path.join('bin', 'icons', 'circular', 'star_red.png'))

        # Set the wizard page text.
        self.setTitle('2. Customize Template')
        self.setSubTitle('')

        # Grab the variables that are being passed to us.
        self.vars = vars

        # Connect signals to slots.
        self.connect(self.ui.settingsList, \
            QtCore.SIGNAL('itemSelectionChanged()'), self.settingSelected)

    def initializePage(self):
        self.variables = []
        self.variable_widgets = []
        self.display_variables = []
        for variable in self.vars['template'].variables:
            # Don't display constants.
            if 'isConstant' in variable.options and \
                variable.options['isConstant'] == 'True':
                continue

            # Don't display tier display options (e.g. tier fonts, colours),
            # but do keep a mapping from the name of the tier to this
            # variable.
            if 'tierDisplayVariable' in variable.options:
                tdv = variable.options['tierDisplayVariable']
                self.display_variables.append((tdv, variable))
                continue

            # Add this variable to our list of variables and to the display.
            self.variables.append(variable)
            item = QtGui.QListWidgetItem(variable.name, self.ui.settingsList)

            # Create a widget tasked with displaying the contents of this
            # variable.
            type = variable.type
            widget = None
            if type == 'directory':
                widget = CuPEDWizardCustomizeDirectory(variable = variable, \
                    variables = self.vars['template'].variables)
            elif type == 'file':
                widget = CuPEDWizardCustomizeFile(variable = variable, \
                    variables = self.vars['template'].variables)
            elif type == 'transcript':
                widget = CuPEDWizardCustomizeTranscript(variable = variable, \
                    variables = self.vars['template'].variables)
            elif type == 'string':
                widget = CuPEDWizardCustomizeString(variable = variable, \
                    variables = self.vars['template'].variables)
            elif type == 'colour' or type == 'color':
                widget = CuPEDWizardCustomizeColour(variable = variable, \
                    variables = self.vars['template'].variables)
            elif type == 'font':
                widget = CuPEDWizardCustomizeFont(variable = variable, \
                    variables = self.vars['template'].variables)
            elif type == 'tier':
                widget = CuPEDWizardCustomizeTier(variable = variable, \
                    variables = self.vars['template'].variables, \
                    display_variables = self.display_variables)
            elif type == 'selection':
                widget = CuPEDWizardCustomizeSelection(variable = variable, \
                    variables = self.vars['template'].variables)

            self.variable_widgets.append(widget)

            # Watch for changes to this widget's values.
            self.connect(widget, QtCore.SIGNAL('updatedChoices'), \
                self.updateValue)

        # Construct a mapping of variable destinations to variable values.
        vmap = dict((v.destination, v.value) for v in self.variables)

        # Update the left-hand list icons associated for each variable.
        for widget in self.variable_widgets:
            # Assign a default value to the variable, if one exists.
            variable = widget.variable
            if variable.default is not None:
                try:
                    variable.assign_choices(variable.default, vmap)
                except Exception, reason:
                    pass

            # Make sure that the widget has been initialized.  (This will
            # fire off an 'updatedChoices' event, once completed)
            widget.initialize()

            # Have this variable also watch for any changes in its parent's
            # values, if such a parent-child dependency exists.
            variable = widget.variable
            if variable.dependency:
                for parent_widget in self.variable_widgets:
                    parent_variable = parent_widget.variable
                    if variable.dependency == parent_variable.name:
                        widget.connect(parent_widget, \
                            QtCore.SIGNAL('updatedChoices'), \
                            widget.parentChanged)
                        break

    def cleanupPage(self):
        # Clear the list of settings if the user hits 'Back'.
        self.ui.settingsList.clear()
        self.ui.settingsList.clearSelection()

        # Remove all custom widgets from the groupbox.
        layout = self.ui.currentSettingGroupBox.layout()
        for child in self.ui.currentSettingGroupBox.children():
            if child is not layout:
                child.setVisible(False)
                self.ui.currentSettingGroupBox.layout().removeWidget(child)

        # Add the old 'settings' label back to the groupbox.
        self.ui.currentSettingGroupBox.layout().addWidget(self.ui.settingsLabel)
        self.ui.settingsLabel.setVisible(True)

    def isComplete(self):
        # Allow the user to move on to the next page once a value has been
        # provided for every required template setting.
        for variable in self.variables:
            if 'isRequired' in variable.options and \
                variable.options['isRequired'] == 'False':
                continue

            if variable.value is None:
                return False

        return True

    def updateValue(self, widget):
        # Update the icons associated with the given widget.
        variable = widget.variable
        item = self.ui.settingsList.item(self.variable_widgets.index(widget))

        # Temporarily disconnect the 'updatedChoices' signal.
        self.disconnect(widget, \
            QtCore.SIGNAL('updatedChoices'), self.updateValue)

        # Attempt to assign any existing choice of variable values to this
        # variable.  (If assignment fails, then the user will be forced to
        # enter a new choice before being able to move on)
        try:
            vmap = dict((v.destination, v.value) for v in self.variables)
            variable.assign_choices(variable.choice, vmap)
        except Exception, reason:
            pass

        # Reconnect the 'updatedChoices' signal.
        self.connect(widget, QtCore.SIGNAL('updatedChoices'), \
            self.updateValue)

        # If this is a transcript, then we go one step further and assign
        # any existing choices of display settings for the tiers in this
        # transcript.
        if variable.type == 'transcript' and variable.value is not None:
            for transcript in variable.value:
                for tier in transcript.tiers:
                    for (tier_name, display_variable) in self.display_variables:
                        if tier_name == tier.name:
                            display_variable.assign_choices \
                                (display_variable.choice, vmap, \
                                 display_variable.type != 'font')

        # If this is an optional variable, use a 'heart' icon.
        if 'isRequired' in variable.options and \
              variable.options['isRequired'] == 'False':
            # If a value has already been assigned, use a green icon.
            if variable.value is not None:
                item.setIcon(self.optionalCompleteIcon)
            # Otherwise, use a blue icon (since this is an optional value).
            else:
                item.setIcon(self.optionalIncompleteIcon)
        # Otherwise, if this is a required variable, use a 'star' icon.
        else:
            # If a value has already been assigned, use a green icon.
            if variable.value is not None:
                item.setIcon(self.requiredCompleteIcon)
            # Otherwise, use a red icon (since this is still required).
            else:
                item.setIcon(self.requiredIncompleteIcon)

        # Alert any listeners of a possible change in the completeness of
        # this wizard page.
        self.emit(QtCore.SIGNAL('completeChanged()'))

    def settingSelected(self):
        # Check for a newly-selected setting.
        items = self.ui.settingsList.selectedItems()
        if len(items) > 0:
            # Set the current variable.
            item = items[0]
            self.variable_index = self.ui.settingsList.row(item)
            self.variable = self.variables[self.variable_index]

            # Set the description of this variable.
            self.ui.descriptionText.setText(self.variable.description)

            # Hide and remove all widgets in the groupbox.
            for child in self.ui.currentSettingGroupBox.children():
                if child is not self.ui.currentSettingGroupBox.layout():
                    child.setVisible(False)
                    self.ui.currentSettingGroupBox.layout().removeWidget(child)

            # Add to the groupbox a widget tasked with editing the currently-
            # selected variable.
            widget = self.variable_widgets[self.variable_index]
            widget.setVisible(True)
            self.ui.currentSettingGroupBox.layout().addWidget(widget)
        else:
            # Remove all custom widgets from the groupbox.
            for child in self.ui.currentSettingGroupBox.children():
                if child is not self.ui.currentSettingGroupBox.layout():
                    child.setVisible(False)
                    self.ui.currentSettingGroupBox.layout().removeWidget(child)

            # Add the old 'settings' label back to the groupbox.
            self.ui.currentSettingGroupBox.layout().addWidget( \
                self.ui.settingsLabel)
            self.ui.settingsLabel.setVisible(True)

class CuPEDWizardPreviewTemplate(QtGui.QWizardPage):
    def __init__(self, parent = None, vars = {}):
        super(CuPEDWizardPreviewTemplate, self).__init__(parent)
        self.ui = Ui_CuPEDWizardPreviewTemplate()
        self.ui.setupUi(self)

        # Grab the variables that are being passed to us.
        self.vars = vars

        # Prepare a space for a temporary directory (for template previews).
        self.temporary_directory = None

        # Connect signals to slots.
        self.connect(self.ui.browseButton, \
            QtCore.SIGNAL('clicked()'), self.browseButtonClicked)
        self.connect(self.ui.outputDirectoryLineEdit, \
            QtCore.SIGNAL('textEdited(QString)'), self.outputDirectoryEdited)

        # Display wizard text.
        self.setTitle('3. Preview Template')
        self.setSubTitle('')
        self.setButtonText(QtGui.QWizard.NextButton, 'Process Template')

    def initializePage(self):
        # Keep more convenient copies of the template to process and its
        # variables.
        self.template = self.vars['template']
        self.variables = self.template.variables

        # If a default output directory exists in the template, show it in the
        # line edit.
        if self.template.output_directory:
            self.ui.outputDirectoryLineEdit.setText \
                (self.template.output_directory)
            self.emit(QtCore.SIGNAL('completeChanged()'))

        # Check to see if this template provides us with a preview.
        if self.template.preview_file_name:
            # If a preview is possible, create a temporary directory in which
            # to store the output.
            self.temporary_directory = tempfile.mkdtemp()
            if os.altsep:
                self.temporary_directory = \
                    self.temporary_directory.replace(os.sep, os.altsep)

            # Prepare the mapping of variable names to variable values that
            # Mako expects.
            variables = {'av' : [self.vars['av']], 'PREVIEW' : [True]}
            for variable in self.variables:
                # Include the dummy eval() statement to make sure that all
                # that can be executed by 'exec' is variable assignment: eval()
                # will raise an exception other than NameError if 'variable.
                # destination' does not resolve to a Python statement.
                #
                # Note that this still doesn't prevent malicious users from
                # executing memory bombs, or even statements like '__import__
                # ('os').remove("arbitrary_file")'.  The latter can probably
                # be avoided in part by restricting globals()['__builtins__']
                # to some minimal list of values -- but the real, long-term
                # solution is to phase out all calls to 'eval()' and 'exec'
                # in CuPED.  Make this a priority.
                #
                # FIXME
                try:
                    try:
                        eval(variable.destination, locals(), variables)
                    except NameError:
                        pass

                    exec '%s = variable.value' % \
                        variable.destination in locals(), variables
                except NameError:
                    warn("Unable to process variable.", \
                         "CuPED is unable to load the variable " + \
                         "'%s'" % variable.name + " for use with the " + \
                         "given template.", traceback.format_exc())

            # Un-list single-element variables before giving them to Mako.
            for key in variables:
                value = variables[key]
                if value == list(value) and len(value) == 1:
                    variables[key] = value[0]

            # Process the template using Mako.
            for template in self.template.templates:
                # Make all paths absolute and create output directories as
                # needed.
                input_file_name = template.input_file_name
                if not os.path.isabs(input_file_name):
                    input_file_name = os.path.join \
                        (self.template.input_directory, input_file_name)
                    if os.altsep:
                        input_file_name = \
                            input_file_name.replace(os.sep, os.altsep)

                output_file_name = template.output_file_name
                if not os.path.isabs(output_file_name):
                    output_file_name = os.path.join \
                        (self.temporary_directory, output_file_name)
                    if os.altsep:
                        output_file_name = \
                            output_file_name.replace(os.sep, os.altsep)

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

                    # Write the rendered contents of the template to the
                    # output file.
                    output_file = open(output_file_name, 'w')
                    output_file.write(mako_template.render(**variables))
                    output_file.close()

                # Otherwise, just copy this file from its input location to
                # its specified output location.
                else:
                    shutil.copy(input_file_name, output_file_name)

            # Prepare the file name to preview.
            preview = os.path.join(self.temporary_directory, \
                self.template.preview_file_name)
            if os.altsep:
                preview = preview.replace(os.sep, os.altsep)

            # Preview the output in the webView widget.
            self.ui.webView.load(QtCore.QUrl('file:///%s' % preview))
        else:
            # Otherwise, let the user know that no preview is available.
            self.ui.webView.setHtml('<html><body style="display: table; ' + \
                'width: 90%; height: 90%"><h3 style="display: ' + \
                'table-cell; vertical-align: middle; color: gray; ' + \
                'font-style: italic; text-align: center">' + \
                '(no preview available)</h3></body></html>')

    def cleanupPage(self):
        # Remove any temporary files which may have been generated for the
        # template preview.
        if self.temporary_directory:
            shutil.rmtree(self.temporary_directory)
            self.temporary_directory = None

    def isComplete(self):
        # Don't let the user move on until a valid output directory has been
        # specified.
        return (self.template.output_directory is not None) and \
               (os.path.isdir(self.template.output_directory))

    def outputDirectoryEdited(self, text):
        if text and os.path.isdir(text):
            self.template.output_directory = str(text)
        else:
            self.template.output_directory = None

        self.emit(QtCore.SIGNAL('completeChanged()'))

    def browseButtonClicked(self):
        # Find the name of the old directory, if one was given.
        old_directory = QtGui.QDesktopServices.storageLocation \
            (QtGui.QDesktopServices.DesktopLocation)
        given_directory = str(self.ui.outputDirectoryLineEdit.text())
        if given_directory and os.path.isdir(given_directory):
            old_directory = given_directory

        # Prompt the user to select an output directory.
        dirname = QtGui.QFileDialog.getExistingDirectory \
            (self, 'CuPED - Open output directory', old_directory)
        if os.altsep:
            dirname = dirname.replace(os.sep, os.altsep)

        # If we have a valid directory, update the template, the text box,
        # and let Qt know that the completeness of this wizard page may
        # have changed.
        if dirname:
            self.template.output_directory = str(dirname)
            self.ui.outputDirectoryLineEdit.setText(dirname)
            self.emit(QtCore.SIGNAL('completeChanged()'))

class CuPEDWizardProcessTemplateThread(QtCore.QThread):
    def __init__(self, parent = None, vars = {}):
        QtCore.QThread.__init__(self, parent)
        self.vars = vars

    def run(self):
        # Prepare the mapping of variable names to variable values that
        # Mako expects.
        variables = {'av' : [self.vars['av']], 'PREVIEW' : [False]}
        for variable in self.vars['template'].variables:
            # Include the dummy eval() statement to make sure that all
            # that can be executed by 'exec' is variable assignment: eval()
            # will raise an exception other than NameError if 'variable.
            # destination' does not resolve to a Python statement.
            #
            # Note that this still doesn't prevent malicious users from
            # executing memory bombs, or even statements like '__import__
            # ('os').remove("arbitrary_file")'.  The latter can probably
            # be avoided in part by restricting globals()['__builtins__']
            # to some minimal list of values -- but the real, long-term
            # solution is to phase out all calls to 'eval()' and 'exec'
            # in CuPED.  Make this a priority.
            #
            # FIXME
            try:
                try:
                    eval(variable.destination, locals(), variables)
                except NameError:
                    pass

                exec '%s = variable.value' % \
                    variable.destination in locals(), variables
            except NameError:
                warn("Unable to process variable.", \
                     "CuPED is unable to load the variable " + \
                     "'%s'" % variable.name + " for use with the " + \
                     "given template.", traceback.format_exc())

        # Un-list single-element variables before giving them to Mako.
        for key in variables:
            value = variables[key]
            if value == list(value) and len(value) == 1:
                variables[key] = value[0]

        # Get the input and output directories (and let the A/V processing
        # tools know where to put their output).
        input_directory = self.vars['template'].input_directory
        output_directory = self.vars['template'].output_directory
        self.vars['av'].set_output_directory(output_directory)

        # Process the template using Mako.
        template_total = len(self.vars['template'].templates)
        template_count = 0
        for template in self.vars['template'].templates:
            # Make all paths absolute and create output directories as needed.
            input_file_name = template.input_file_name
            if not os.path.isabs(input_file_name):
                input_file_name = os.path.join(input_directory, \
                    input_file_name)
                if os.altsep:
                    input_file_name = input_file_name.replace(os.sep, os.altsep)

            output_file_name = template.output_file_name
            if not os.path.isabs(output_file_name):
                output_file_name = os.path.join \
                    (output_directory, output_file_name)
                if os.altsep:
                    output_file_name = \
                        output_file_name.replace(os.sep, os.altsep)

                if not os.path.exists(os.path.dirname(output_file_name)):
                    os.mkdir(os.path.dirname(output_file_name))

            # Inform all listeners that we're processing another file.
            template_count = template_count + 1
            self.emit(QtCore.SIGNAL('processingFile(QString, int, int)'), \
                template.input_file_name, template_count, template_total)

            # If this template should be processed, feed it into Mako and
            # store the result in the output directory under the names
            # specified in the template metadata.
            if template.should_be_processed:
                # Give Mako the template file.
                mako_template = mako.template.Template \
                    (input_encoding = 'utf-8', output_encoding = 'utf-8', \
                     filename = input_file_name)

                # Write the rendered contents of the template to the output
                # file.
                output_file = open(output_file_name, 'w')
                output_file.write(mako_template.render(**variables))
                output_file.close()
            # Otherwise, just copy this file from its input location to its
            # specified output location.
            else:
                shutil.copy(input_file_name, output_file_name)

class CuPEDWizardProcessTemplate(QtGui.QWizardPage):
    def __init__(self, parent = None, vars = {}):
        super(CuPEDWizardProcessTemplate, self).__init__(parent)
        self.ui = Ui_CuPEDWizardProcessTemplate()
        self.ui.setupUi(self)

        # Grab a local copy of the variables that are being passed to us.
        self.vars = vars

        # Have we finished processing this template?
        self.is_finished = False

        # Set wizard text.
        self.setTitle('4. Processing Template')
        self.setSubTitle('')

    def initializePage(self):
        # Clear the text display and reset the progress bar and the label.
        self.ui.detailsTextEdit.clear()
        self.ui.processingProgressBar.reset()
        self.ui.processingLabel.setText('Processing template...')

        # We're not done processing yet.
        self.is_finished = False
        self.emit(QtCore.SIGNAL('completeChanged()'))

        # Watch the 'avtools' interface for console output.
        self.vars['av'].add_console_listener(self.updateBuffer)

        # Start the thread that will process the template files, listening for
        # its signals in order to update the GUI.
        self.thread = CuPEDWizardProcessTemplateThread(vars = self.vars)
        self.connect(self.thread, \
            QtCore.SIGNAL('processingFile(QString, int, int)'), \
            self.processingFile)
        self.connect(self, QtCore.SIGNAL('newTextAdded(QString)'), \
            self.realUpdateBuffer)
        self.connect(self.thread, QtCore.SIGNAL('finished()'), self.threadDone)
        self.thread.start()

    def cleanupPage(self):
        # Stop listening for console output from the 'avtools' interface.
        self.vars['av'].remove_console_listener(self.updateBuffer)

    def isComplete(self):
        return self.is_finished

    def updateBuffer(self, new_text):
        # Pass along the updated text via a signal. (Avoids having a worker
        # thread update the GUI)
        self.emit(QtCore.SIGNAL('newTextAdded(QString)'), \
            QtCore.QString(new_text))

    def realUpdateBuffer(self, new_text):
        # Add any new console output from 'avtools' to the details text box.
        self.ui.detailsTextEdit.insertPlainText(new_text)

    def processingFile(self, file_name, file_count, files_total):
        # Whenever a new file is processed, update the progress label text.
        self.ui.processingLabel.setText('Processing "%s" (%d of %d)' % \
            (file_name, file_count, files_total))

        # Update the progress bar's degree of completion.
        self.ui.processingProgressBar.setMinimum(0)
        self.ui.processingProgressBar.setMaximum(files_total)
        self.ui.processingProgressBar.setValue(file_count)

    def threadDone(self):
        self.is_finished = True
        self.emit(QtCore.SIGNAL('completeChanged()'))

class CuPEDWizardAboutCuPED(QtGui.QDialog):
    def __init__(self, parent = None):
        super(CuPEDWizardAboutCuPED, self).__init__(parent)
        self.ui = Ui_CuPEDWizardAboutCuPED()
        self.ui.setupUi(self)

        # Close this window when the 'OK' button is clicked.
        self.connect(self.ui.okButton, QtCore.SIGNAL('clicked()'), self.close)

        # Open any URLs that the user clicks on in the info box with an
        # external web browser.
        self.connect(self.ui.infoWebView, \
            QtCore.SIGNAL('linkClicked(const QUrl&)'), self.openUrl)

        # TODO: Move this into a separate file.
        credits = ''' \
            <center>
                <h3>About <b style="color: #ff2b3d">CuPED</b> %s</h3>
                <h4>Acknowledgements</h4>
            </center>

            <p>
            CuPED was developed by
            <a href="http://www.ualberta.ca/~cdcox/">Christopher Cox</a>
            and <a href="http://www.uweb.ucsb.edu/~aberez/">Andrea Berez</a>.
            The authors would like to acknowledge the contributions of several
            individuals to CuPED development and testing:
            </p>

            <ul>
                <li><a href="http://ra.tapor.ualberta.ca/Dinka/">Kristina
                    Geeraert</a> &mdash; Dinka transcripts</li>
                <li><a href="http://www.uaf.edu/anlc/staff.html">Jim Kari</a>
                    &mdash; Dena'ina transcripts</li>
                <li><a href="http://www.stephaniemorse.com">Stephanie Morse</a>
                    &mdash; CuPED artwork</li>
                <li><a href="http://www.ualberta.ca/~srice/">Sally Rice</a>
                    &mdash; Dene Suline transcripts</li>
                <li><a href="http://qenaga.org">qenaga.org</a> &mdash;
                    Dena'ina transcripts</li>
                <li><a href="http://movingmemory.blogspot.com/">Peter Wiens</a>
                    &mdash; Plautdietsch transcripts</li>
            </ul>

            <p>
            CuPED incorporates icons from the 'circular' icon theme, developed
            by <a href=
            "http://prothemedesign.com/free-webdesign-tools/circular-icons/">
            Ben Gillbanks</a>
            (<a href="http://creativecommons.org/licenses/by/2.5/">Creative
            Commons Attribution 2.5 Generic</a> license), and from
            the 'Tango' icon theme, developed by contributors to the
            <a href="http://tango.freedesktop.org">Tango Project</a>
            (<a href="http://creativecommons.org/licenses/by-sa/2.5/">Creative
            Commons Attribution-Share Alike 2.5 Generic</a> license).
            While CuPED gratefully acknowledges its use of these resources,
            this should not be taken to indicate in any way an endorsement
            of CuPED by these independent developers.
            </p>

            <p>
            CuPED also relies on several open-source software packages to
            process transcript media and templates.  For more information,
            please see the
            <a href="http://sweet.artsrn.ualberta.ca/cdcox/cuped">CuPED
            website</a>.
            </p>
        ''' % cuped.settings.Settings().getVersion()

        # Display some basic acknowledgements, and don't let the user leave
        # this page.
        self.ui.infoWebView.setHtml(credits)
        self.ui.infoWebView.page().setLinkDelegationPolicy \
            (QtWebKit.QWebPage.DelegateAllLinks)
        self.ui.infoWebView.show()

    def openUrl(self, url):
        # Don't load the page in the info box itself, but rather open the
        # given URL in the appropriate external application.
        self.ui.infoWebView.stop()
        QtGui.QDesktopServices.openUrl(url)

class CuPEDWizardFinishedTemplate(QtGui.QWizardPage):
    def __init__(self, parent = None, vars = {}):
        super(CuPEDWizardFinishedTemplate, self).__init__(parent)
        self.ui = Ui_CuPEDWizardFinishedTemplate()
        self.ui.setupUi(self)

        # Grab local copies of the variables that we're being given.
        self.vars = vars
        self.config = self.vars['cfg']

        # Create an instance of the 'About CuPED' window.
        self.about = CuPEDWizardAboutCuPED()

        # Has the template that the user just filled in been saved?
        self.has_saved = False

        # Connect signals to slots.
        self.connect(self.ui.saveTemplateButton, \
            QtCore.SIGNAL('clicked()'), self.saveTemplateButtonClicked)
        self.connect(self.ui.openTemplateButton, \
            QtCore.SIGNAL('clicked()'), self.openTemplateButtonClicked)
        self.connect(self.ui.openDirectoryButton, \
            QtCore.SIGNAL('clicked()'), self.openDirectoryButtonClicked)
        self.connect(self.ui.anotherTemplateButton, \
            QtCore.SIGNAL('clicked()'), self.anotherTemplateButtonClicked)
        self.connect(self.ui.aboutCuPEDButton, \
            QtCore.SIGNAL('clicked()'), self.aboutCuPEDButtonClicked)

        # Set the wizard page's text.
        self.setTitle('Congratulations!')
        self.setSubTitle('CuPED has finished processing your template. ' + \
            'You can safely close this window, or select from one of ' + \
            'the following options to continue working with the processed ' + \
            'template.')

    def initializePage(self):
        # Save a convenience copy of the template.
        self.template = vars['template']

        # Only allow users to open the template if there's a preview file
        # specified (otherwise, there are any number of potential candidates
        # for processed files to open, and us with little way of chosing
        # between them).
        preview = os.path.join(self.template.output_directory, \
            self.template.preview_file_name)
        if os.altsep:
            preview = preview.replace(os.sep, os.altsep)

        self.ui.openTemplateButton.setEnabled \
            ((self.template.preview_file_name is not None) and \
             (os.path.isfile(preview)))

        # Only allow users to open the output directory if it actually exists.
        self.ui.openDirectoryButton.setEnabled \
            (os.path.isdir(self.template.output_directory))

    def saveTemplateButtonClicked(self):
        # Prompt the user for a file name under which to save the filled-
        # in template.
        qfname = QtGui.QFileDialog.getSaveFileName(self, \
            'CuPED - Save template', QtGui.QDesktopServices.storageLocation \
             (QtGui.QDesktopServices.DocumentsLocation), \
            'CuPED templates (*.xml)')
        if not qfname:
            return

        # Before actually saving the template to XML, cull any display
        # variables that are no longer in use.
        display_variables = []
        standard_variables = {}
        for variable in self.template.variables:
            if 'tierDisplayVariable' in variable.options:
                display_variables.append(variable)
            else:
                standard_variables[variable.name] = variable

        for variable in display_variables:
            tier = variable.options['tierDisplayVariable']
            dependency = variable.dependency

            # Only preserve variables whose dependencies exist and whose
            # choices are valid.  (Note that all display variables will have
            # transcripts as their dependencies, and so we're safe asking
            # for the names of tiers here)
            if dependency in standard_variables:
                standard_variable = standard_variables[dependency]
                if tier in [t.name for t in standard_variable.value[0].tiers]:
                    continue

            # Remove all other display variables from this template.
            self.template.variables.remove(variable)

        # Prepare the input and output directories in the template for saving.
        cuped_directory = os.path.abspath(os.curdir)
        if os.altsep:
            cuped_directory = cuped_directory.replace(os.sep, os.altsep)

        self.template.input_directory = \
            self.template.input_directory.replace(cuped_directory, '%CuPED%')
        self.template.output_directory = \
            self.template.output_directory.replace(cuped_directory, '%CuPED%')

        # Save the template as XML under the given file name.
        try:
            output_file = open(str(qfname), 'w')
            output_file.write(self.template.__xml__())
            output_file.close()
        except Exception, reason:
            warn("Unable to save template.", \
                 "CuPED is unable to save the current template.  Please " + \
                 "ensure that the location you choose to save the " + \
                 "template to is accessible.", traceback.format_exc())
            return

        # The template has been saved!
        self.has_saved = True

        # Add the newly-saved template to the list of known templates, if it's
        # not already in the list.
        fname = str(qfname)
        templates = self.config.get('general', 'templates')
        if templates:
            templates = eval(templates)
        else:
            templates = []

        if fname not in templates:
            templates.append(fname)
            self.config.set('general', 'templates', '%s' % templates)
            self.config.save()

    def openTemplateButtonClicked(self):
        # Get the name of the processed file that should be opened.
        f = os.path.join(self.template.output_directory, \
            self.template.preview_file_name)
        if os.altsep:
            f = f.replace(os.sep, os.altsep)

        # Open the template with the default application for files of this
        # kind on this platform.
        if os.path.isfile(f):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl('file:///%s' % f))
        else:
            self.initializePage()

    def openDirectoryButtonClicked(self):
        # Get the name of the output directory.
        output_directory = self.template.output_directory
        if os.altsep:
            output_directory = output_directory.replace(os.sep, os.altsep)

        # Open the output directory using the default system application for
        # this purpose (e.g. Windows Explorer, Finder, etc.)
        if os.path.isdir(output_directory):
            QtGui.QDesktopServices.openUrl \
                (QtCore.QUrl('file:///%s' % output_directory))
        else:
            self.initializePage()

    def anotherTemplateButtonClicked(self):
        # If the template that the user just filled in hasn't been saved yet,
        # ask them if they're sure they want to get rid of it.
        if not self.has_saved:
            msg = QtGui.QMessageBox()
            msg.setIconPixmap(QtGui.QPixmap(os.path.join \
                ('bin', 'icons', 'cuped', 'Cupedplain-64x64.png')))
            msg.setText('Save the current template?')
            msg.setInformativeText('CuPED can save a copy of the ' + \
                'template you just completed for later use.  This ' + \
                'allows you to reprocess your ELAN transcripts without ' + \
                'needing to complete all of the preceding prompts again.')
            msg.setStandardButtons(QtGui.QMessageBox.Save | \
                QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel)
            choice = msg.exec_()

            # If the user chose to save this template, then go through the
            # whole template saving process with them.
            if choice == QtGui.QMessageBox.Save:
                self.saveTemplateButtonClicked()
            # If the user chose to cancel, return to the wizard page.
            elif choice == QtGui.QMessageBox.Cancel:
                return

        # Restart the wizard.
        self.vars['wizard'].restart()

    def aboutCuPEDButtonClicked(self):
        # Show the 'About CuPED' window.
        self.about.exec_()


if __name__ == '__main__':
    # Before setting up the GUI, make sure that there is a list of available
    # templates in the configuration file.  If not, initialize that list with
    # the templates that come bundled with CuPED.
    configuration = cuped.settings.Settings()
    if not configuration.get('general', 'templates'):
        templates = []
        for dir, subdirs, files in \
            os.walk(os.path.join(os.path.abspath(os.curdir), 'templates')):
            for file in files:
                if file.endswith('.xml'):
                    try:
                        tm = cuped.template.TemplateMetadata \
                            (os.path.join(dir, file))
                        templates.append(os.path.join(dir, file))
                    except Exception:
                        pass

        if templates:
            configuration.set('general', 'templates', '%s' % templates)
            configuration.save()

    # Initialize the GUI.
    app = QtGui.QApplication(sys.argv)

    # Prepare artwork for the wizard.
    watermark = QtGui.QPixmap(os.path.join( \
        'bin', 'icons', 'cuped', 'Cupedlotsofhearts-opaque_small.png'))
    logo = QtGui.QPixmap(os.path.join( \
        'bin', 'icons', 'cuped', 'Cupedplain-64x64.png'))
    background = QtGui.QPixmap(os.path.join( \
        'bin', 'icons', 'cuped', 'Cupedlotsofhearts-opaque.png'))

    # Create the wizard.
    wizard = QtGui.QWizard()

    # Set an icon for this window on all platforms but OSX.
    if platform.uname()[0] != 'Darwin':
        wizard.setWindowIcon(QtGui.QIcon(os.path.join( \
            'bin', 'icons', 'cuped', 'Cupedplain-64x64.png')))

    # Get an implementation of the 'avtools' interface (or die trying).
    try:
        avtools = cuped.avtools.AVTools(impl = cuped.ffmpeg_qt_avtools.ffmpegQtAVTools)
    except Exception:
        warn("Unable to process media files.", \
             "CuPED is unable to find an implementation of the A/V " + \
             "processing tools that it uses to work with transcript " + \
             "media.", traceback.format_exc())
        sys.exit(1)

    # Create a dictionary for state shared between pages, then create the
    # pages themselves.
    vars = {}
    vars['cfg'] = configuration
    vars['av'] = avtools
    vars['wizard'] = wizard
    pages = [CuPEDWizardWelcome(vars = vars), \
        CuPEDWizardChooseTemplate(vars = vars), \
        CuPEDWizardCustomizeTemplate(vars = vars), \
        CuPEDWizardPreviewTemplate(vars = vars), \
        CuPEDWizardProcessTemplate(vars = vars), \
        CuPEDWizardFinishedTemplate(vars = vars)]

    # Add each of the pages to the wizard once that page's graphics have been
    # set up.
    for page in pages:
        page.setPixmap(QtGui.QWizard.WatermarkPixmap, watermark)
        page.setPixmap(QtGui.QWizard.LogoPixmap, logo)
        page.setPixmap(QtGui.QWizard.BackgroundPixmap, background)
        app.connect(app, QtCore.SIGNAL('lastWindowClosed()'), page.cleanupPage)
        wizard.addPage(page)

    # Set the height of this wizard window.  We wouldn't usually care about
    # this, but there's a bug in Qt 4.4 under Windows where the window
    # would grow larger than the screen could fit at the preview page.  This
    # may have been fixed in Qt 4.5, but until new Python bindings are
    # available, we set the size here.
    #
    # FIXME
    if platform.uname()[0] == 'Windows':
        wizard.setFixedHeight(500)
        
    wizard.setWindowTitle('CuPED')
    wizard.show()

    sys.exit(app.exec_())
