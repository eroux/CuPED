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

class AVTools(object):
    def __new__(cls, impl = None, *args, **kwargs):
        if impl in AVTools.__subclasses__():
            index = AVTools.__subclasses__().index(impl)
            subclass = AVTools.__subclasses__()[index]
            if subclass._is_available():
                return super(cls, subclass).__new__(subclass)

        for subclass in AVTools.__subclasses__():
            if subclass._is_available():
                return super(cls, subclass).__new__(subclass)

        raise Exception, 'No avtools interface available'

    @staticmethod
    def _is_available():
        """Is this implementation of avtools available on this platform?"""
        raise NotImplementedError

    def get_output_directory(self):
        """Returns the current output directory."""
        raise NotImplementedError

    def set_output_directory(self, output_directory):
        """
        Sets the directory into which all output files with relative paths
        will be placed.
        """
        raise NotImplementedError

    def add_console_listener(self, console_callback):
        """
        Adds the given callback to the list of methods which should be
        called whenever new console output is produced by the media processing
        tool.  This assumes that the given method takes a string as its sole
        argument, representing the text printed to the console since the
        last time this callback was invoked.
        """
        raise NotImplementedError

    def remove_console_listener(self, console_callback):
        """
        Removes the given callback from the list of methods which should
        be called whenever new console output is produced.
        """
        raise NotImplementedError

    def get_available_audio_output_formats(self):
        """
        Returns a dictionary relating identifiers for audio formats accepted
        by this implementation to brief descriptions of the audio formats
        themselves.
        """
        raise NotImplementedError

    def get_available_image_output_formats(self):
        """
        Returns a dictionary relating identifiers for image formats accepted
        by this implementation to brief descriptions of the image formats
        themselves.
        """
        raise NotImplementedError

    def get_available_video_output_formats(self):
        """
        Returns a dictionary relating identifiers for video formats accepted
        by this implementation to brief descriptions of the video formats
        themselves.
        """
        raise NotImplementedError

    def get_duration(self, input_file_name):
        """
        Returns the total playtime of the given media file, in milliseconds.
        """
        raise NotImplementedError

    def get_dimensions(self, input_file_name):
        """
        Returns a tuple containing the pixel width and height of the given
        video file, or (-1, -1) if no such dimensions can be extracted.
        """
        raise NotImplementedError

    def extract_clip(self, input_video_file_name, input_video_start_time_ms, \
            input_video_end_time_ms, input_audio_file_name, \
            input_audio_start_time_ms, input_audio_end_time_ms, \
            output_file_name, output_video_format = 'copy', \
            output_audio_format = 'copy', output_dimensions = (-1, -1)):
        """
        Extract the segment of the given input media file which starts and ends
        at the given millisecond positions, ensuring that the resulting clip is
        encoded in the specified audio and video formats and (for video) is of
        the given height and width (by default, the same dimensions as the
        input).
        """
        raise NotImplementedError

    def extract_image(self, input_file_name, time_ms, output_file_name, \
            output_image_format, output_dimensions = (-1, -1), \
            console_callback = None, progress_callback = None):
        """
        Extract a still image from the given time position (in milliseconds) in
        the input video file, ensuring that the resulting image file is saved in
        the specified image format and is of the given height and width (by
        default, the same dimensions as the input video).
        """
        raise NotImplementedError

    def convert(self, input_file_name, output_file_name, 
            output_video_format = 'copy', output_audio_format = 'copy', \
            output_dimensions = (-1, -1), console_callback = None, \
            progress_callback = None):
        """
        Convert the entire input file into the specified audio and video
        formats, ensuring (for video) that the resulting file is of the given
        height and width (by default, the same dimensions as the input).
        """
        return self.extract_clip(input_file_name, 0, \
            self.get_duration(input_file_name), output_file_name, \
            output_video_format, output_audio_format, output_dimensions, \
            console_callback, progress_callback)

# HACK
import ffmpeg_avtools
import ffmpeg_qt_avtools
