"""
DSN means: "domain specific nerf" (the name is obviously tentative)

The idea is: in many subparts of the application, we apply the same pattern:

* a structure
* a Clef (set of notes that operate on that structure)
* play_... & construct_... can be used to combine the 2.

In principle, a single structure can have multiple clefs defined on it, so grouping all of the above in a single
directory is a bit of a shortcut. But as it stands, multiple clefs per structure haven't arisen yet; so we're just
grouping them all in a single directory.
"""
