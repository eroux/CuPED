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

class Transcript(object):
    def __new__(cls, trs = None, impl = None, *args, **kwargs):
        if trs:
            if impl in Transcript.__subclasses__():
                index = Transcript.__subclasses__().index(impl)
                subclass = Transcript.__subclasses__()[index]
                if subclass.can_load(trs):
                    return super(cls, subclass).__new__(subclass)

            for subclass in Transcript.__subclasses__():
                if subclass.can_load(trs):
                    return super(cls, subclass).__new__(subclass)

            raise Exception, 'No Transcript interface available'

        return object.__new__(cls)

    def __init__(self, trs = None):
        # The location of the transcript file itself.
        self.transcript_location = None

        # The media associated with this transcript, if any.  Represented
        # here as a list of triples: (media_file_location, media_mime_type,
        # media_playback_offset).
        self.media = []

        # A list of TranscriptTier objects, representing the levels of
        # annotation present in this Transcript.
        self.tiers = []

        # A list of TranscriptAnnotation objects, representing the contents
        # of all tiers of this Transcript.
        self.annotations = []

        # If a transcript file has been provided, try to load it.  (This
        # serves a dual purpose here, preventing instantiations of this
        # class from an actual transcript (since this is meant to be abstract),
        # and providing useful default behaviour to all subclasses)
        if trs:
            self.load(trs)

    @staticmethod
    def can_load(transcript_file):
        """Is the given file a transcript that can be loaded by this class?"""
        raise NotImplementedError

    def load(self, transcript_file):
        """
        Opens and parses the given transcript.  If successful, the contents
        of the given transcript will be represented in the fields of this
        object.
        """
        raise NotImplementedError

class TranscriptTier(object):
    def __init__(self):
        # The name of this tier within the transcript.
        self.name = None

        # Are annotations within this tier associated with timed segments of
        # the transcript's media?
        self.is_time_aligned = False

        # The TranscriptTier which introduces this tier in the transcript.  If
        # no parent tier exists, this will be None.
        self.parent_tier = None

        # The TranscriptTier objects which depend upon this tier.  If no child
        # tiers exist, this list will be empty.
        self.child_tiers = []

        # The TranscriptAnnotation objects representing all annotations found
        # within this tier of the transcript.  If this tier contains no
        # annotations, then this list will be empty.
        self.annotations = []

        # Display options.

        # The fonts which should be used to display this tier.  These are
        # listed as CuPEDFont objects in order of preference, from most
        # preferred (first element) to least preferred (last element).
        self.fonts = []

        # The preferred foreground colour (CuPEDColour) of this tier.
        self.foreground_colour = None

        # The preferred background colour (CuPEDColour) of this tier.
        self.background_colour = None

        # Is this tier visible?
        self.is_visible = True

class TranscriptAnnotation(object):
    def __init__(self):
        # A unique identifier assigned by ELAN to this annotation.
        self.name = None

        # The TranscriptTier in which this annotation appears.  All valid
        # annotations have some TranscriptTier associated with them; this
        # should never be None once a transcript has been loaded.
        self.tier = None

        # The TranscriptAnnotation upon which this annotation depends.  If no
        # parent annotation exists, this has the value of None.
        self.parent_annotation = None

        # The TranscriptAnnotation objects which depend upon this annotation.
        # If this annotation has no children, this list will be empty.
        self.child_annotations = []

        # The TranscriptAnnotation objects which overlap in time with this
        # annotation.  This includes not only child annotations (which, by
        # definition, must overlap in time with their parent), but also
        # annotations on other, hierarchically-unrelated tiers which occur
        # within the same time range.
        self.overlapping_annotations = []

        # The starting time of this annotation in the associated media files,
        # in milliseconds.
        self.time_start = -1

        # The ending time of this annotation in the associated media files,
        # in milliseconds.
        self.time_end = -1

        # The contents of this annotation.
        self.value = None

# HACK
import elan_transcript
