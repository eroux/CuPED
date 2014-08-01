<%
##
## Note: Adobe Flash Player 8 (or later) may be required to view the web
##          pages produced by this template in synchrony with the embedded
##         media.  (It may be possible to view such pages with Flash Player 7,
##         as well, although not all features may be supported; this has
##         not yet been tested)
##

# TODO: This should really just take a user-specified 'primary' media file,
#        chosen from among the files listed the transcript (if multiple media
#        files are present), rather than just defaulting to the first ones in
#        the list.  (That would also help us make sure that at least one
#        media file is present)
#
#        FIXME

# Hackish convenience functions: might this be a audio/video file?  (We
# should really be relying on ffmpeg to tell us this, especially with some
# container formats being capable of carrying either an audio or a video
# stream, but this should hopefully do for the time being)
def might_be_video(fn):
    if not fn: return False
    fn = fn.lower()
    return fn.endswith('.m4v') or fn.endswith('.mp4') or \
           fn.endswith('.vob') or fn.endswith('.avi') or \
           fn.endswith('.mov')

def might_be_audio(fn):
    if not fn: return False
    fn = fn.lower()
    return fn.endswith('.wav') or fn.endswith('.mp3') or \
           fn.endswith('.aif') or fn.endswith('.aiff') or \
           fn.endswith('.ogg')

# Loop through the available media, find the first video and the first audio
# files (in the order that they were listed in ELAN).
input_audio_file = None
input_audio_file_playback_offset = -1
input_audio_file_duration = -1
input_video_file = None
input_video_file_playback_offset = -1
input_video_file_duration = -1

media_width = -1
media_height = -1

# By default, we don't use a splash image (i.e. for audio).
splash_image = None;

# FIXME: this should handle multiple video/audio streams more gracefully.
for (input_media_file, input_mime_type, playback_offset) in transcript.media:
    if input_audio_file is None and (input_mime_type.startswith('audio/') or
                                     might_be_audio(input_media_file)):
        input_audio_file = input_media_file
        input_audio_file_playback_offset = playback_offset
        input_audio_file_duration = av.get_duration(input_audio_file)

    elif input_video_file is None and (input_mime_type.startswith('video/') or
                                       might_be_video(input_media_file)):
        input_video_file = input_media_file
        input_video_file_playback_offset = playback_offset
        input_video_file_duration = av.get_duration(input_video_file)
        (media_width, media_height) = av.get_dimensions(input_video_file)

        # Create a snapshot from the video to use as the player splash image.
        splash_image = 'data/splash.jpg'
        av.extract_image(input_video_file, 125, splash_image, 'jpeg')

# Calculate total durations.
input_media_file_duration = max(input_audio_file_duration, \
                                input_video_file_duration)

output_media_file_duration = \
    max(input_audio_file_duration - input_audio_file_playback_offset, \
        input_video_file_duration - input_video_file_playback_offset)

# TODO: This should really have separate modes (i.e., a binary, user-supplied
#        variable) for audio or video processing (and default to whichever
#        one is most appropriate for this MIME type, if possible).
#
#        FIXME

# If we can't get the dimensions of the video, then assume we're dealing
# with audio only, and set some reasonable default dimensions for the
# player.  (Note that this wraps the MP3 file in an FLV container; this
# unfortunately appears to be necessary with the version of Flowplayer
# being used here)
# 
# (This is really an unfair assumption -- it could be that 'av' is choking on
# a video file, instead -- but this should be good enough for now.)
is_audio_file = (input_audio_file is not None)
if media_width == -1 or media_height == -1:
    is_audio_file = True
    media_height = 25

output_media_file = 'data/output.flv'
if should_convert_media and not PREVIEW:
    av.extract_clip(input_video_file, \
        input_video_file_playback_offset, input_video_file_duration, \
        input_audio_file, \
        input_audio_file_playback_offset, input_audio_file_duration, \
        output_media_file, \
        output_video_format = 'flv', output_audio_format = 'mp3')
%>\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<title>${title}</title>
<script type="text/javascript" src="js/flowplayer-3.2.8.min.js"></script>

<script type="text/javascript">
    //<![CDATA[
    // Check which annotation we're in every 50 milliseconds.
    var updateInterval = 50;

    // An array of annotations and their starting and ending times, in milli-
    // seconds.
    var annotations = [
%for a in primary_tier.annotations:
        { 'id': '${a.name}', 'start': ${a.time_start / 1000.0}, 'end': ${a.time_end / 1000.0} },
%endfor
    ];

    // Reference to the current annotation being played.
    var currentAnnotation = null;

    // ID of the timer which tracks the end of annotations.
    var endAnnotationTimer = null;

    // Are we playing an annotation for the user right now?
    var inPlayAnnotation = false;

%if not PREVIEW:
    window.onload = function() {
        flowplayer("CuPED-global-player-object", "swf/flowplayer-3.2.8.swf",

            // Flash settings for Flowplayer and its plugins.
            {
                clip: {
                    // Load the clip itself.
                    url: "../data/output.flv",
                    autoPlay: false,
                    initialScale: 'scale',
                    loop: false,

                    onSeek: function() {
                        if (! inPlayAnnotation) {
                            clearTimeout(endAnnotationTimer);
                        }
                    },

                    onPause: function() {
                        clearTimeout(endAnnotationTimer);
                    },


                    onStart: function() {
                        // Hide the overlay "play" button on start-up.
                        this.getPlugin("play").hide();
                    },

                    onStop: function() {
                        // Show the overlay "play" button again once stopped.
                        clearTimeout(endAnnotationTimer);
                        this.getPlugin("play").show();
                    }
                },

                plugins: {
                    controls: {
                        // Load the controls.
                        url: 'swf/flowplayer.controls-3.2.8.swf',

                        // Show the scrubber, but not the timer.
                        scrubber: true,
                        time: false,

                        // Hide the stop button, the mute button, the full-
                        // screen button, the playlist button, and the volume
                        // controls.
                        stop: false,
                        volume: false,
                        fullscreen: false,
                        playlist: false,
                        mute: false,

                        backgroundColor: '#000',
## If we're dealing with audio only.
%if splash_image is None:
                        autoHide: false,
%endif
                    }
                },

                // Once the player has been initialized (and the splash image
                // clicked), begin watching for changes in the current
                // annotation and start the media playing.
                //
                // The idea behind this is that the JavaScript polls the
                // player every 'updateInterval' milliseconds to see if we've
                // entered into a new annotation.  If we have, then the
                // display is updated.
                onLoad: function() {
                    currentAnnotation = null;
                    setInterval(checkAnnotation, updateInterval);
## If we have a splash image, then clicking on it should start playback.
%if splash_image is not None:
                    $f("CuPED-global-player-object").play();
%endif
                },

                onError: function(errorCode, errorMessage) {
                    alert("Flowplayer: " + errorCode + ": " + errorMessage);
                }
            }
        );
    }
%endif

    // Returns the annotation in which this time (in milliseconds) occurs, or
    // null if this time is not associated with an annotation.
## TODO: Rewrite this, either as a hash or some form of search tree -- the
##          current linear search is just plain inefficient.
    function findAnnotation(time_ms) {
        for (var i = 0; i < annotations.length; i++) {
            annotation = annotations[i];
            if ((time_ms >= annotation.start) && (time_ms <= annotation.end)) {
                return annotation;
            }
        }

        return null;
    }

    // Scroll to a position where the annotation is in the specified spot
    // on the screen ('top', 'middle', 'bottom', 'none' (no tracking)).
    function scrollToAnnotation(annotation, position) {
        // If we shouldn't scroll to follow the current annotation, skip this
        // code.
        if (position == 'none') {
            return;
        }

        // Get the current scroll position.
        scrollPosition = 0;
        if (document.body & document.body.scrollTop) {
            scrollPosition = document.body.scrollTop;
        } else if (document.documentElement && document.documentElement.scrollTop) {
            scrollPosition = document.documentElement.scrollTop;
        } else if (window.pageYOffset) {
            scrollPosition = window.pageYOffset;
        }

        // Get the height of the current window.
        windowHeight = 0;
        if (typeof(window.innerHeight) == 'number') {
            windowHeight = window.innerHeight;
        } else if (document.documentElement && document.documentElement.clientHeight) {
            windowHeight = document.documentElement.clientHeight;
        } else if (document.body && document.body.clientHeight) {
            windowHeight = document.body.clientHeight;
        }

        // Get the height of the entire document.
        documentHeight = document.body.scrollHeight;

        // Get the height of the media player.
        mediaHeight = ${media_height};

        // Get the y-position of the annotation in the page.
        div = document.getElementById(annotation.id);
        divPosition = div.offsetTop;
        while (div = div.offsetParent) {
            divPosition += div.offsetParent;
        }

        finalPosition = divPosition;
        if (position == 'top') {
            finalPosition = divPosition - mediaHeight - 10;
        } else if (position == 'middle') {
            finalPosition = divPosition - mediaHeight - 
                ((windowHeight - mediaHeight) / 2) +
                (document.getElementById(annotation.id).offsetHeight / 2);
        } else if (position == 'bottom') {
            finalPosition = divPosition - windowHeight + 
                document.getElementById(annotation.id).offsetHeight + 10;
        } else {
            return;
        }

        window.scrollTo(0, finalPosition);
    }

    function setCurrentAnnotation(annotation) {
        // Unset the current annotation, if there is one.
        if (currentAnnotation != null) {
            var anElement = document.getElementById(currentAnnotation.id);
            var m = anElement.className.match(' CuPED-current-annotation'); 
            anElement.className = anElement.className.replace(m, '');
        }

        // Set the current annotation to be the one given, if one was provided.
        if (annotation != null) {
            var anElement = document.getElementById(annotation.id);
            anElement.className += ' CuPED-current-annotation';

            // Scroll to the new element.
            scrollToAnnotation(annotation, 'middle');
        }

        // Finally, keep a reference to the current annotation.
        currentAnnotation = annotation;
    }

    // Callback: check the Flowplayer instance to find out what annotation
    // we're in and update the display as necessary.
    function checkAnnotation() {
        closestAnnotation = 
            findAnnotation($f("CuPED-global-player-object").getTime());
        if (closestAnnotation != currentAnnotation) {
            setCurrentAnnotation(closestAnnotation);
        }
    }

    // Callback: when an annotation is done, pause the player.
    function onEndAnnotation() {
        inPlayAnnotation = false;
        $f("CuPED-global-player-object").pause();
        clearTimeout(endAnnotationTimer);
    }

    // User wishes to play the annotation with the given ID and starting time
    // (in seconds).
    function playAnnotation(start_time, end_time) {
        // Start the media playing, then seek to the start of the annotation.
        inPlayAnnotation = true;
        $f("CuPED-global-player-object").play();
        $f("CuPED-global-player-object").seek(start_time);

        // Set a time-out to play just until the end of this annotation.
        endAnnotationTimer = setTimeout(onEndAnnotation, (end_time - start_time) * 1000);
    }
    //]]>
</script>
<%
# Get the primary tier and all of its child tiers into a list.
primary_tiers = []
tier_queue = [primary_tier]
while len(tier_queue) > 0:
    tier = tier_queue.pop()
    if tier not in primary_tiers:
        primary_tiers.append(tier)
        tier_queue = tier_queue + tier.child_tiers
%>

<style type="text/css">
    .CuPED-annotations {
        font-family: sans-serif;
        font-size: larger;
        background: white;
## Make the top bar a little smaller in the preview.  This is a temporary
## measure, and should only be needed until we upgrade to Qt 4.5 (where a
## bug affecting QWizard window heights is fixed).
##
## FIXME
%if PREVIEW:
        margin-top: 115px;
%else:
        margin-top: ${media_height + 15}px;
%endif
     }
    .CuPED-annotation { margin-bottom: 1em; border-collapse: collapse }
    .CuPED-annotation-player { text-align: center; vertical-align: middle }
    .CuPED-annotation-line { }
    .CuPED-annotation-text { padding-right: 1em }
    .CuPED-current-annotation {
        background: #B6E8FF;
        -moz-border-radius: 5px;
        -webkit-border-radius: 5px;
        border-radius: 5px;
    }

## TODO: There should be a separate setting for player placement (if this
##         isn't going to be something that can be adjusted in the browser).
##
##    /* Floating top-right player. */
##    .CuPED-global-player {
##        width: ${media_width}px;
##        height: ${media_height}px;
##        background: black;
##        border: 4px solid lightblue;
##        z-index: 1;
##
##        position: fixed;
##        top: 25px;
##        right: 25px;
##    }
##
##
    /* Fixed titlebar player. */
    .CuPED-global-player {
        width: 100%;
## Make the top bar a little smaller in the preview.  This is a temporary
## measure, and should only be needed until we upgrade to Qt 4.5 (where a
## bug affecting QWizard window heights is fixed).
##
## FIXME
%if PREVIEW:
        height: 100px;
%else:
        height: ${media_height}px;
%endif
        background: black;
        border-bottom: 4px solid #add8e6;
        z-index: 1;

        position: fixed;
        top: 0px;
        left: 0px;
    }

%for tier in primary_tiers:
    .CuPED-annotation-tier-${primary_tiers.index(tier)} {
    %if tier.fonts:
        font-family: \
        %for font in tier.fonts:
"${font.font_name}"\
            %if tier.fonts.index(font) < len(tier.fonts) - 1:
, \
            %else:
;
            %endif
        %endfor
        ## Use the display attributes of the first font by default.
<% font = tier.fonts[0] %>\
        %if font.font_size > -1:
        font-size: ${int(font.font_size)}pt;
        %endif
        %if font.is_bold:
        font-weight: bold;
        %endif
        %if font.is_italic:
        font-style: italic;
        %endif
        %if font.is_underline:
        text-decoration: underline;
        %endif
        %if font.is_strike_through:
        text-decoration: line-through;
        %endif
        %if font.is_small_caps:
        font-variant: small-caps;
        %endif
    %endif
    %if tier.foreground_colour:
        color: ${tier.foreground_colour};
    %endif
    %if tier.background_colour:
        background-color: ${tier.background_colour};
    %endif
    %if not tier.is_visible:
        display: none;
    %endif
    }
%endfor
</style>

## The great IE5/6 fixed positioning hack.  Avert thine eyes, children.
## (c/o http://hem.fyristorg.com/g-force/test/fixedlayer.htm)
<!--[if gte IE 5]>
<style type="text/css">
html, body { height: 100%; overflow-y: hidden; }
.CuPED-annotations { height: 100%; width: 100%; overflow: auto; margin: 0; padding: 0; }
.CuPED-global-player { position: absolute; z-index: 1; }
</style>
<![endif]-->
</head>
<body>

<div class="CuPED-global-player">
%if media_width < 0:
    <div id="CuPED-global-player-object" style="width:100%;height:${media_height}px;">
%else:
    <div id="CuPED-global-player-object" style="width:${media_width}px;height:${media_height}px;">
%endif
%if not PREVIEW and splash_image is not None:
        <img src="${splash_image}" />
%endif
    </div>
</div>

<div class="CuPED-annotations">
%for annotation in primary_tier.annotations:
    <%
    # Gather together the annotations on each of the primary tiers that are
    # children of the current annotation.
    tier_annotations = dict((t.name, []) for t in primary_tiers)
    annotation_queue = [annotation]
    while len(annotation_queue) > 0:
        a = annotation_queue.pop()
        tier_annotations[a.tier.name] = [a] + tier_annotations[a.tier.name]
        annotation_queue = annotation_queue + filter(lambda x: x.tier in \
            primary_tiers, a.child_annotations)

    # Get the maximum number of annotations in any of the primary tiers.
    # (We need this value to determine how many columns to have in the HTML
    # table which houses this annotation and its children)
    max_number_annotations_in_tier = \
        max([len(x) for x in tier_annotations.values()])

    # We haven't added the player to this tier yet.
    have_added_player = False
    %>
    <table class="CuPED-annotation" id="${annotation.name}">
    %for tier in primary_tiers:
        <tr class="CuPED-annotation-line CuPED-annotation-tier-${primary_tiers.index(tier)}">
        %if not have_added_player:
            <% have_added_player = True %>
            <td rowspan="${len(primary_tiers)}">
## TODO: Provide an option to use thumbnails, rather than just the speaker?
                <img src="img/speaker.png" alt="Play annotation" onclick="playAnnotation(${annotation.time_start / 1000.0}, ${annotation.time_end / 1000.0})" />
            </td>
        %endif
        ## If this is the primary tier, then we need to span all columns and
        ## just print it out.
        %if annotation.tier.name == tier.name:
            <td colspan="${max_number_annotations_in_tier}" class="CuPED-annotation-text">
                ${annotation.value | h}
            </td>
        ## If this is one of the child tiers, then we need to be a little more
        ## careful: there can be no children (in which case we print out an
        ## empty tier), or there can be some children, each of which then needs
        ## to be printed in its own <td> element.
        %else:
            %if len(tier_annotations[tier.name]) > 0:
                %for item in tier_annotations[tier.name]:
            <td colspan="${max_number_annotations_in_tier / len(tier_annotations[tier.name])}" class="CuPED-annotation-text">
                ${item.value | h}
            </td>
                %endfor
            %else:
            <td colspan="${max_number_annotations_in_tier}" class="CuPED-annotation-text">
            </td>
            %endif
        %endif
        </tr>
    %endfor
    </table>
%endfor
</div>
</body>
</html>
