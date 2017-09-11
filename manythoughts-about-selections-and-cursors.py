
# What about cursor updates?
# This _can_ be easily expressed.... but might become a bit unwieldy?
# In particular: any cursor update is part of the clef... even when the actual selection isn't changed.

# But who cares...
# 1. we aren't doing this the Nout-way anyway.
# 2. even if we were, we could introduce some kind of rewriting rules? I.e. tricks about forgetting the past? This could
# be a nice example for testing for such things.

# What about t-stability?
# This is maybe harder to express?
# Yes, because the knowledge about which transformations you'd wish to query is stored in the Selection's structure.

# hmmm... draw it?

# Or... you'd just say "let the editor take care of this"

# Or... "It's just a 'set' operation"

# Or... implement some other general interface


# Hmmm... het algemene idee is toch wel goed om over na te denken.
# Het gaat namelijk om: querying as part of the clef. Een ander voorbeeld zou kunnen zijn: kijk op de klok. Of: trek een
# random getal.


# Hmm... wat ik hier nou echt van vind?!

# Aan de andere kant; geen harde noodzaak om hier super puriteins in te zijn: selection heeft nu eenmaal te maken met
# zowel de structuur van de editor als

# toch is dit het eerste voorbeeld van Notes die, om de note te bepalen, ook kennis moeten hebben van de bestaande
# structuur.

# Nog 1x over nadenken?

#
# By the way, there is another similar question on the horizon:
# Vim changes the meaning of certain keys depending on whether you're in selection mode or not. (although in the current
# setup we don't replicate this behavior). The example I can think of is "o" which means either "open new line" or
# "switch to other end".

# This question is entirely similar to the question about "how to implement t-address stability notes?" I mentioned
# above. Here's why: to determine whether an "o" will result in the creation of a "SwitchToOtherEnd" or a note from the
# editor-clef (we don't currently implement "new line", but that's a detail) is in fact determined by the current state
# of the Selection.

# We also have something like this in the case of our "vim structure". if such a structure exists, it's the end-point of
# all key-presses.

# In the case of the 2 examples (double meaning of "o", and "vim receives keypresses first"), I can imagine yet another
# score which unifies stuff. namely: the series of pressed keys (and mouse clicks).

# Yet another question:
# I am about to introduce a structure that is separate from the main editor structure, although it is very closely
# related. In fact, in many cases its notes will be the result of a note on the main editor being played. How should I
# connect these 2 scores (and is this important at all)?


# Or.... just formulate the note "Main Structure Changed"... this is very similar to what I did for the scroll window.
# This also gets rid of the concept of "querying" (you can just take the whole trees and examine those). The trees are
# "cheap", because they can be expressed as a single nout hash.

# Next question: is there a difference "user moved cursor", "anybody moved cursor"?
# I don't think so...  the cursor is either connected to some end (in which case the end simply follows the cursor) or
# not (in which case the fringe/edge must take care of t-stability)

# This last solution I like best.
# I'll just store the full editor_ds object for starters; noting that, if we're ever to make the editor's score using
# Nouts and such, we can do further optimizations.
