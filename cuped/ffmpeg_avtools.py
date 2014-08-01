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
import platform
import re
import shutil
import subprocess
import tempfile
import time

import avtools
import settings

class ffmpegAVTools(avtools.AVTools):
    ffmpeg_video_parameters = {
        'mp4' : ['-vcodec', 'libx264', '-b', '512k', '-flags' '+loop+mv4', \
                 '-cmp', '256', '-partitions', \
                 '+parti4x4+parti8x8+partp4x4+partp8x8+partb8x8', \
                 '-me_method', 'hex', '-subq', '7', '-trellis', '1', \
                 '-refs', '6', '-bf', '16', '-b_strategy', '1', \
                 '-flags2', '+bpyramid+wpred+mixed_refs+dct8x8', \
                 '-coder', '1', '-me_range', '16', '-g', '250', \
                 '-keyint_min', '25', '-sc_threshold', '40', \
                 '-i_qfactor', '0.71', '-qmin', '10', '-qmax', '51', \
                 '-qdiff', '4'],
        'flv' : ['-vcodec', 'flv', '-qcomp', '0.6', '-qmax', '15', \
                 '-qdiff', '4', '-i_qfactor', '0.71', '-b_qfactor', '0.76', \
                 '-b', '512k'],
        'copy' : ['-vcodec', 'copy'],
        'none' : ['-vn']
    }

    ffmpeg_audio_parameters = {
        'mp3' : ['-acodec', 'libmp3lame', '-ab', '192k', '-ar', '44100', \
                 '-ac', '2'],
        'aac' : ['-acodec', 'libfaac', '-ab', '192k', '-ar', '44100', \
                 '-ac', '2'],
        'wav' : ['-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2'],
        'copy' : ['-acodec', 'copy'],
        'none' : ['-an'],
    }

    ffmpeg_executable = ''
    yamdi_executable = ''

    @staticmethod
    def _is_available():
        systems = {'Windows' : 'win32', 'Darwin' : 'osx'}
        extensions = {'Windows' : '.exe', 'Darwin' : ''}
        variables = [('ffmpeg', 'ffmpeg_executable'), \
                     ('yamdi', 'yamdi_executable')]

        configuration = settings.Settings()

        plat = platform.uname()[0]
        system = systems.get(plat)
        extension = extensions.get(plat)
        if not extension:
            extension = ''

        # Make sure that each of the variables exists.
        for (name, variable) in variables:
            # Check the configuration file for a stored location.
            value = configuration.get('utilities', name)
            if value is not None and os.path.isfile(value):
                setattr(ffmpegAVTools, variable, value)
                configuration.set('utilities', name, value)
                continue

            # Check the CuPED directory for a bundled binary.
            if system:
                value = os.path.join(os.path.abspath(os.curdir), 'bin', \
                    system, '%s%s' % (name, extension))
                if os.altsep:
                    value = value.replace(os.sep, os.altsep)

                if os.path.isfile(value):
                    setattr(ffmpegAVTools, variable, value)
                    configuration.set('utilities', name, value)
                    continue

            # Check for binaries in the system path.  (Create a list of all
            # possible paths of this binary, then filter out all paths which
            # don't refer to actual files)
            binaries = filter(lambda x: os.path.isfile(x), \
                [os.path.join(p, '%s%s' % (name, extension)) \
                for p in os.environ['PATH'].split(os.pathsep)])
            if binaries:
                setattr(ffmpegAVTools, variable, binaries[0])
                configuration.set('utilities', name, binaries[0])
                continue

            # If no binary can be found, then this interface can't be used.
            return False

        # If all binaries were found, then this interface can be used.
        configuration.save()
        return True

    def __init__(self, impl = None):
        # By default, use the current working directory as the output
        # directory.
        self.output_directory = os.curdir

        # Assume no listeners to console output or progress events.
        self.console_listeners = []

        # Windows work-around: hide the console when 'subprocess' is called.
        self._startupinfo = None
        if platform.uname()[0] == 'Windows':
            self._startupinfo = subprocess.STARTUPINFO()
            self._startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    def get_output_directory(self):
        """Returns the current output directory."""
        return self.output_directory

    def set_output_directory(self, output_directory):
        """
        Sets the directory into which all output files with relative paths
        will be placed.
        """
        self.output_directory = output_directory

    def add_console_listener(self, console_callback):
        """
        Adds the given callback to the list of methods which should be
        called whenever new console output is produced by the media processing
        tool.  This assumes that the given method takes a string as its sole
        argument, representing the text printed to the console since the
        last time this callback was invoked.
        """
        self.console_listeners.append(console_callback)

    def remove_console_listener(self, console_callback):
        """
        Removes the given callback from the list of methods which should
        be called whenever new console output is produced.
        """
        if console_callback in self.console_listeners:
            self.console_listeners.remove(console_callback)

    def get_available_audio_output_formats(self):
        """
        Returns a dictionary relating identifiers for audio formats accepted
        by this implementation to brief descriptions of the audio formats
        themselves.
        """
        return { \
            'mp3' : 'MPEG-2 Layer 3 audio (*.MP3)', \
            'aac' : 'Advanced Audio Coding audio (*.AAC)', \
            'wav' : 'Microsoft WAV audio (*.WAV)', \
            'copy' : 'Same format as the input file (direct copy)', \
            'none' : 'No audio', \
        }

    def get_available_image_output_formats(self):
        """
        Returns a dictionary relating identifiers for image formats accepted
        by this implementation to brief descriptions of the image formats
        themselves.
        """
        return {
            'png' : 'Portable network graphics (*.PNG)', \
            'jpeg' : 'JPEG image format (*.JPG, *.JPEG)', \
        }

    def get_available_video_output_formats(self):
        """
        Returns a dictionary relating identifiers for video formats accepted
        by this implementation to brief descriptions of the video formats
        themselves.
        """
        return { \
            'mp4' : 'MPEG-4 (H.264) video (*.MP4)', \
            'flv' : 'Flash Video format (*.FLV)', \
            'copy' : 'Same format as the input file (direct copy)', \
            'none' : 'No video', \
        }

    def to_timestamp(self, time_ms):
        """
        Converts the given millisecond value into a timestamp string in ffmpeg
        format (hh:mm:ss.xx).
        """
        v = time_ms
        return '%02d:%02d:%02d.%02d' % (((v / 1000) / 60) / 60, \
             ((v / 1000) / 60) % 60, (v / 1000) % 60, (v % 100))

    def from_timestamp(self, timestamp):
        """
        Converts the given timestamp string (hh:mm:ss.xx) into milliseconds.
        """
        match = re.compile(r'(\d\d):(\d\d):(\d\d).(\d\d\d?)').match(timestamp)
        if match:
            return (int(match.group(1)) * 60 * 60 * 1000) + \
                (int(match.group(2)) * 60 * 1000) + \
                (int(match.group(3)) * 1000) + \
                (int(match.group(4)))

        return -1

    def get_ffmpeg_file_information(self, input_file_name):
        """
        Returns a file-like object containing information from ffmpeg about
        about the given media file.
        """
        # Call ffmpeg to get basic information about this file, if it exists
        # and can be parsed by ffmpeg.  All output is stored in a temporary
        # file, which will be automatically removed upon garbage collection.
        output_buffer = tempfile.TemporaryFile()
        status = subprocess.call([ffmpegAVTools.ffmpeg_executable, '-i', \
            input_file_name], stdout = output_buffer, stderr = output_buffer, \
            startupinfo = self._startupinfo)

        output_buffer.seek(0)
        return output_buffer

    def get_duration(self, input_file_name):
        """
        Returns the total playtime of the given media file (in milliseconds) or
        -1 if the playtime of the given file cannot be retrieved by ffmpeg.
        """
        # Parse the ffmpeg output for this file, looking for a duration
        # timestamp that can be converted into milliseconds.
        file_information = self.get_ffmpeg_file_information(input_file_name)
        duration_re = re.compile(r'Duration: (.*?),')
        for line in file_information:
            match = duration_re.search(line)
            if match is not None:
                return self.from_timestamp(match.group(1))

        return -1

    def get_dimensions(self, input_file_name):
        """
        Returns a tuple containing the pixel width and height of the given
        video file, or (-1, -1) if no such dimensions can be extracted.
        """
        file_information = self.get_ffmpeg_file_information(input_file_name)
        dimensions_re = re.compile(r'Video: .*?, .*?, (\d+)x(\d+)')
        for line in file_information:
            match = dimensions_re.search(line)
            if match is not None:
                return (int(match.group(1)), int(match.group(2)))

        return (-1, -1)

    def extract_clip(self, input_video_file_name, input_video_start_time_ms, \
            input_video_end_time_ms, input_audio_file_name, \
            input_audio_start_time_ms, input_audio_end_time_ms, \
            output_file_name, output_video_format = 'none', \
            output_audio_format = 'none', output_dimensions = (-1, -1)):
        """
        Extract the segment of the given input media file which starts and ends
        at the given millisecond positions, ensuring that the resulting clip is
        encoded in the specified audio and video formats and (for video) is of
        the given height and width (by default, the same dimensions as the
        input).
        """
        # Get the desired output height and width.  If either one is -1, then
        # use the same dimensions as the input file.
        height, width = output_dimensions
        (original_height, original_width) = (-1, -1)
        if (height == -1 or width == -1) and input_video_file_name:
            (original_height, original_width) = \
                self.get_dimensions(input_video_file_name)

        if height == -1:
            height = original_height
        if width == -1:
            width = original_width

        # Get ffmpeg audio and video encoding parameter lists.  If the user
        # has supplied us with an unknown format, complain coherently about
        # it.
        try:
            audio_parameters = \
                ffmpegAVTools.ffmpeg_audio_parameters[output_audio_format]
        except Exception:
            raise Exception, 'unknown audio format: %s' % output_audio_format

        try:
            video_parameters = \
                ffmpegAVTools.ffmpeg_video_parameters[output_video_format]
        except Exception:
            raise Exception, 'unknown video format: %s' % output_video_format

        # If the output file is not given as an absolute path, then make sure
        # it gets placed in the output directory by default.  (That is, all
        # relative paths are interpreted here as being relative to the output
        # directory).
        #
        # Also, if the output file asks to be stored in a directory which
        # doesn't exist, create that directory for it and put the file in
        # there (or die trying).
        if not os.path.isabs(output_file_name):
            dir = os.path.abspath(os.path.join(self.output_directory, \
                os.path.dirname(output_file_name)))
            if not os.path.exists(dir):
                os.mkdir(dir)

            output_file_name = os.path.abspath \
                (os.path.join(dir, os.path.basename(output_file_name)))

        # Prepare the ffmpeg command.
        command = [ffmpegAVTools.ffmpeg_executable, '-y']

        # If there's a video file, add video processing information.
        if input_video_file_name is not None:
            command.extend([ \
                '-i', input_video_file_name, \
                '-ss', '%s' % self.to_timestamp(input_video_start_time_ms), \
                '-t', '%s' % self.to_timestamp(input_video_end_time_ms - \
                                               input_video_start_time_ms) ])

            if output_video_format != 'none' and height > -1 and width > -1:
                command.extend(['-s', '%dx%d' % (int(height), int(width))])

        if video_parameters is not None:
            command.extend(video_parameters)

        if input_audio_file_name is not None:
            command.extend([ \
                '-i', input_audio_file_name, \
                '-ss', '%s' % self.to_timestamp(input_audio_start_time_ms), \
                '-t', '%s' % self.to_timestamp(input_audio_end_time_ms - \
                                               input_audio_start_time_ms) ])

        if audio_parameters is not None:
            command.extend(audio_parameters)

        # If there are separate audio and video sources, make sure they're
        # mapped appropriately.
        if input_video_file_name is not None and \
           input_audio_file_name is not None:

            # Figure out which stream inside the video file is actually the
            # video stream, taking '0:0' as our default.
            video_stream = '0:0'
            file_information = self.get_ffmpeg_file_information(input_video_file_name)
            match = (re.compile(r'Stream #(...).*?:\s*Video:')).search(file_information)
            if match is not None:
                video_stream = str(match.group(1)).replace('.', ':')

            command.extend(['-map', video_stream, '-map', '1:0'])

        command.extend([output_file_name])

        # Invoke ffmpeg, redirecting stderr to stdout (and stdout to the
        # internal 'subprocess' pipe).
        ffmpeg = subprocess.Popen(command, stdout = subprocess.PIPE, \
            stderr = subprocess.STDOUT, startupinfo = self._startupinfo)

        # Alert the caller to any new console output from this process.
# FIXME: This blocks until the process is completed.  Is there any safe way
#        of getting the output as it comes?
        console_output = ffmpeg.communicate()[0]
        if console_output:
            for callback in self.console_listeners:
                callback(console_output)

        return ffmpeg.returncode

    def extract_image(self, input_file_name, time_ms, output_file_name, \
            output_image_format, output_dimensions = (-1, -1)):
        """
        Extract a still image from the given time position (in milliseconds) in
        the input video file, ensuring that the resulting image file is saved
        in the specified image format and is of the given height and width (by
        default, the same dimensions as the input video).
        """
        # Get the desired output height and width.  If either one is -1, then
        # use the same dimensions as the input file.
        height, width = output_dimensions
        if height == -1 or width == -1:
            (original_height, original_width) = \
                self.get_dimensions(input_file_name)

        if height == -1:
            height = original_height
        if width == -1:
            width = original_width

# FIXME: this should raise an exception if *no* dimensions can be extracted
#        from the file (e.g. if we're given an audio file).

        # Make sure the output file name has the proper file extension.  (This
        # is needed to make ffmpeg guess the image format)
        extension = ''
        if output_image_format == 'png' and \
           not output_file_name.endswith('.png'):
            extension = '.png'
        elif output_image_format == 'jpeg' and \
             (not output_file_name.endswith('.jpg') or \
              not output_file_name.endswith('.jpeg')):
            extension = '.jpg'

        # If the output file is not given as an absolute path, then make sure
        # it gets placed in the output directory by default.  (That is, all
        # relative paths are interpreted here as being relative to the output
        # directory).
        #
        # Also, if the output file asks to be stored in a directory which
        # doesn't exist, create that directory for it and put the file in
        # there.
        if not os.path.isabs(output_file_name):
            dir = os.path.abspath(os.path.join(self.output_directory, \
                os.path.dirname(output_file_name)))
            if not os.path.exists(dir):
                os.mkdir(dir)

            output_file_name = os.path.abspath \
                (os.path.join(dir, os.path.basename(output_file_name)))

        # Invoke ffmpeg.
        ffmpeg = subprocess.Popen([ffmpegAVTools.ffmpeg_executable, \
            '-i', input_file_name, '-y', '-t', '1', '-f', 'image2', \
            '-ss', '%s' % self.to_timestamp(time_ms), \
            '-s', '%dx%d' % (int(height), int(width)), \
            "%s%s" % (output_file_name, extension)], \
             stdout = subprocess.PIPE, stderr = subprocess.STDOUT, \
             startupinfo = self._startupinfo)

        # Alert the caller to any new console output from this process.
# FIXME: This blocks until the process is completed.  Is there any safe way
#        of getting the output as it comes?
        console_output = ffmpeg.communicate()[0]
        if console_output:
            for callback in self.console_listeners:
                callback(console_output)

        # If we needed to add an extension to get ffmpeg to work, remove that
        # extension afterwards.
        if extension:
            shutil.move('%s%s' % (output_file_name, extension), \
                output_file_name)

        return ffmpeg.returncode


# TODO: how to specify audio bitrate/sample frequency/channels/etc.?
#        how to specify video bitrate/etc.?
#                --> maybe 'AVToolsAudioProfile', '...VideoProfile'?
# TODO: how to do / where to allow users to specify two-pass (for video)?



# DEBUG
if __name__ == '__main__':
    av = avtools.AVTools(impl = ffmpegAVTools)
    input_files = ['/Users/chris/Desktop/CuPED/CuPED/_Sources/Aupelkoose/Aupelkoose-hqmp4.mp4']
#    input_files = ['/Users/chris/Desktop/CuPED/CuPED/_Sources/Aupelkoose/Aupelkoose-hqmp4.mp4', '/Users/chris/Desktop/CuPED/CuPED/_Sources/Beaver/beaver.wav']
    counter = 0
    for input in input_files:
        counter = counter + 1
        print '---'
        print "Input file: %s" % input

        # Confirm that we can round-trip timestamps.
        print "DURATION: %d" % av.get_duration(input)
        print "DURATION: %s" % av.to_timestamp(av.get_duration(input))
        print "DURATION: %d" % av.from_timestamp(av.to_timestamp(av.get_duration(input)))
        print "DURATION: %s" % av.to_timestamp(av.from_timestamp(av.to_timestamp(av.get_duration(input))))
        print ''

        (width, height) = av.get_dimensions(input)
        print "DIMENSIONS: %d x %d" % (width, height)
        print ''

        print av.extract_image(input, 1000, '/Users/chris/Desktop/CuPED/snapshot-%s.png' % counter, 'png')
        print av.extract_image(input, 1000, '/Users/chris/Desktop/CuPED/snapshot-%s.jpg' % counter, 'jpeg')

        print av.extract_clip(input, 0, 5000, '/Users/chris/Desktop/CuPED/clip-%s.mp4' % counter)

        # Double the playback dimensions of the clip.
        print av.extract_clip(input, 0, 5000, '/Users/chris/Desktop/CuPED/bigclip-%s.mp4' % counter, output_video_format = 'mp4', output_dimensions = (width * 2, height * 2))

        # Convert the entire file to some other format.
        print av.convert(input, '/Users/chris/Desktop/CuPED/converted-%s.flv' % counter, output_audio_format = 'mp3', output_video_format = 'flv')

        # Produce just an MP3 track from this video.
        print av.convert(input, '/Users/chris/Desktop/CuPED/justaudio-%s.mp3' % counter, output_audio_format = 'mp3', output_video_format = 'none')

        # Produce a WAV track from this video.
        print av.convert(input, '/Users/chris/Desktop/CuPED/justaudio-%s.wav' % counter, output_audio_format = 'wav', output_video_format = 'none')

