#
# 'basic_template.txt'
#

# Variables in the template.
'directory':  ${directory}
'file':       ${file}
'transcript': ${transcript.transcript_location}
'string':     ${string}
'colour':     ${colour}
'font':       ${font}
'tier':       ${tier.name}
'selection':  ${selection}

# Print out all of the tiers in the given transcript.
%for t in transcript.tiers:
${t.name} - \
    %if t.parent_tier is None:
No parent tier.
    %else:
Parent tier "${t.parent_tier.name}"; ${len(t.annotations)} annotations.
    %endif
    * Tier fonts: ${t.fonts}
    * Tier foreground colour: ${t.foreground_colour}
    * Tier background colour: ${t.background_colour}
    * Tier is visible? ${t.is_visible}
%endfor
