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
import urllib
import xml.etree.ElementTree as etree

import transcript

class ELANTranscript(transcript.Transcript):
    def _guessMIMEType(self, file_path, file_suffix):
        """Tries to guess the MIME type of the given file."""
        return ''

    @staticmethod
    def can_load(transcript_file):
        """Is the given file a transcript that can be loaded by this class?"""
        try:
            # Attempt to load in the transcript as an XML document.  (This
            # is massively inefficient; in future revisions, consider just
            # parsing the ANNOTATION_DOCUMENT tag, instead)
            tree = etree.parse(transcript_file)
            root = tree.getroot()

            # Confirm that the root element of the transcript is indeed an
            # ANNOTATION_DOCUMENT tag, and that it nominally complies with an
            # MPI-published schema for ELAN.
            schema = 'http://www.mpi.nl/tools/elan/EAF'
            ns = '{http://www.w3.org/2001/XMLSchema-instance}'
            attrib = 'noNamespaceSchemaLocation'
            return root.tag == 'ANNOTATION_DOCUMENT' and \
                   root.attrib['%s%s' % (ns, attrib)].startswith(schema)
        except:
            return False

    def load(self, transcript_file):
        """
        Opens and parses the given ELAN transcript file.  If successful, the
        contents of the transcript will be represented in the fields of this
        object.
        """

        # Load the ELAN XML document.
        tree = etree.parse(transcript_file)
        root = tree.getroot()

        # Get the full path to the given transcript file and store it in the
        # Transcript object.
        self.transcript_location = os.path.abspath(transcript_file)

        # Get the media files associated with this transcript.
        for t in root.findall('HEADER/MEDIA_DESCRIPTOR'):
            media_url = t.attrib['MEDIA_URL']
            media_file_location = None
            try:
                (media_file_location, _ignore) = urllib.urlretrieve(media_url)
            except Exception:
                try:
                    (media_file_location, _ignore) = \
                        urllib.urlretrieve[t.attrib['RELATIVE_MEDIA_URL']]
                except Exception:
                    media_file_location = None

            media_mime_type = t.attrib['MIME_TYPE']
            if media_mime_type.find('*'):
                media_mime_type = \
                    self._guessMIMEType(self.transcript_location, \
                    media_mime_type[media_mime_type.rfind('.')])

            media_playback_offset = 0
            if 'TIME_ORIGIN' in t.attrib.keys():
                media_playback_offset = int(t.attrib['TIME_ORIGIN'])

            self.media.append((media_file_location, media_mime_type, \
                media_playback_offset))

        # Now populate the Transcript with tiers and annotations.

        # Create a mapping from linguistic types to their time-alignability.
        type_is_time_alignable = dict((t.attrib['LINGUISTIC_TYPE_ID'], \
            t.attrib['TIME_ALIGNABLE'] == 'true') for t in \
            root.findall('LINGUISTIC_TYPE'))

        # Create a mapping from timeslot_id to time_value.
        timeslots = {}
        for t in root.findall('TIME_ORDER/TIME_SLOT'):
            if 'TIME_VALUE' in t.attrib:
                timeslots[t.attrib['TIME_SLOT_ID']] = \
                    int(t.attrib['TIME_VALUE'])
            else:
                timeslots[t.attrib['TIME_SLOT_ID']] = None

        # Create a mapping from user-defined types to ELAN stereotypes.
        linguistic_types_to_constraints = {}
        for lt in root.findall('LINGUISTIC_TYPE'):
            lt_id = lt.attrib['LINGUISTIC_TYPE_ID']
            if 'CONSTRAINTS' in lt.keys():
                linguistic_types_to_constraints[lt_id] = \
                    lt.attrib['CONSTRAINTS']
            else:
                linguistic_types_to_constraints[lt_id] = ''

        # Create mappings from tier names to tier objects, and from tier names
        # to the names of their parent tier (if any).
        tier_name_to_tier = {}
        tier_name_to_parent_tier_name = {}

        # Create a mapping from annotation IDs to annotation instances.
        annotation_id_to_annotation = {}

        # Create tiers and anotations.
        for t in root.findall('TIER'):
            tier = ELANTranscriptTier()
            tier.name = t.attrib['TIER_ID']
            tier.is_time_aligned = \
                type_is_time_alignable[t.attrib['LINGUISTIC_TYPE_REF']]

            # Set up parent and child tier references.  These will be turned
            # into references to the objects themselves later on.
            tier_name_to_tier[tier.name] = tier
            if 'PARENT_REF' in t.attrib.keys():
                tier_name_to_parent_tier_name[tier.name] = \
                    t.attrib['PARENT_REF']

            # Get the constraint stereotype for this tier.
            tier.constraint_stereotype = \
                linguistic_types_to_constraints[t.attrib['LINGUISTIC_TYPE_REF']]

            # Now parse the annotations for this tier.
            for a in t:
                annotation = transcript.TranscriptAnnotation()
                annotation.tier = tier
                annotation.name = a[0].attrib['ANNOTATION_ID']

                # If this is a time-aligned annotation, then retrieve both its
                # start and end times.
                if a[0].tag == 'ALIGNABLE_ANNOTATION':
                    annotation.time_start = \
                        timeslots[a[0].attrib['TIME_SLOT_REF1']]
                    annotation.time_end = \
                        timeslots[a[0].attrib['TIME_SLOT_REF2']]
                # If this is not a time-aligned annotation, then it must have
                # a reference to a parent annotation.  The ID of the parent
                # annotation is hackishly stored in that field for now, and
                # processed into an object reference later on.
                else:
                    annotation.parent_annotation = \
                        a[0].attrib['ANNOTATION_REF']

                # Get the annotation value.
                annotation.value = a[0][0].text

                tier.annotations.append(annotation)
                self.annotations.append(annotation)
                annotation_id_to_annotation[annotation.name] = annotation

            self.tiers.append(tier)

        # Establish parent-child tier relationships.
        for tier in self.tiers:
            # If this tier has a parent, then store a reference to the parent
            # tier within this object.
            if tier.name in tier_name_to_parent_tier_name:
                tier.parent_tier = \
                    tier_name_to_tier[tier_name_to_parent_tier_name[tier.name]]

                # If this child tier hasn't already been registered with the
                # parent, do so now.
                if tier not in tier.parent_tier.child_tiers:
                    tier.parent_tier.child_tiers.append(tier)

        # ELAN does not presently store parent annotation references for time-
        # aligned annotations.  That is, no ANNOTATION_REF attribute is 
        # present in ELAN transcripts for annotations found in 'Included In' or
        # 'Time Subdivision'-type tiers, even when parent annotations for these
        # annotations do exist.
        #
        # As a work-around, time stamps are compared here, finding annotations
        # in the child tiers which occur within the time bounds of annotations
        # in the parent tiers.
        for tier in self.tiers:
            if tier.constraint_stereotype == 'Included_In' or \
               tier.constraint_stereotype == 'Time_Subdivision':

                preceding_start_time = -1
                following_end_time = -1
                annotations = []

                for a in tier.annotations:
                    # We'll not only assign parents at this point, but also
                    # fill in missing timecodes.  (It turns out that ELAN
                    # doesn't necessarily record time codes for all
                    # annotations on these kinds of tiers, unfortunately)
                    if a.time_start is not None:
                        preceding_start_time = a.time_start
                        annotations = [a]
                    else:
                        annotations.append(a)

                    if a.time_end is not None:
                        following_end_time = a.time_end

                        # Update the start and end times in cases where
                        # these are be missing.
                        if len(annotations) > 1:
                            time_increment = (following_end_time - \
                                preceding_start_time) / len(annotations)
                            for i in range(0, len(annotations)):
                                annotations[i].time_start = \
                                    int(preceding_start_time + \
                                        (i * time_increment))

                                if annotations[i].time_end is None:
                                    annotations[i].time_end = \
                                        int(preceding_start_time + \
                                            ((i +1) * time_increment))

                        annotations = []
                    else:
                        if not a in annotations:
                            annotations.append(a)

                    # Assign parent-child associations.
                    for parent_annotation in tier.parent_tier.annotations:
                        if parent_annotation.time_start <= a.time_start and \
                           parent_annotation.time_end >= a.time_end:
                            a.parent_annotation = parent_annotation
                            parent_annotation.child_annotations.append(a)
                            break
            else:
                # For annotations on non-time-aligned tiers, replace parent
                # annotation IDs with references to the actual instances
                # of those annotations.
                for a in tier.annotations:
                    if a.parent_annotation is not None:
                        a.parent_annotation = \
                            annotation_id_to_annotation[a.parent_annotation]
                        a.parent_annotation.child_annotations.append(a)

class ELANTranscriptTier(transcript.TranscriptTier):
    def __init__(self):
        transcript.TranscriptTier.__init__(self)

        # The ELAN constraint stereotype associated with this tier.  Possible
        # values include 'Included_In', 'Symbolic_Association',
        # 'Symbolic_Subdivision', 'Time_Subdivision', and '' (the default
        # stereotype)
        self.constraint_stereotype = ''
