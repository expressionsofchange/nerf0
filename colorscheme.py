# from kivy.utils import rgba
from kivy.utils import get_color_from_hex
from kivy.compat import string_types


def rgba(s, *args):
    '''Return a Kivy color (4 value from 0-1 range) from either a hex string or
    a list of 0-255 values.

    .. versionadded:: 1.9.2
    '''
    if isinstance(s, string_types):
        return get_color_from_hex(s)
    elif isinstance(s, (list, tuple)):
        s = map(lambda x: x / 255., s)
        return s
    elif isinstance(s, (int, float)):
        s = map(lambda x: x / 255., [s] + list(args))
        return s
    raise Exception('Invalid value (not a string / list / tuple)')


background = rgba(255, 255, 255, 255)
color0 = rgba(0, 0, 0, 255)
color1 = rgba(153, 0, 0, 255)
color2 = rgba(115, 0, 230, 255)
color3 = rgba(0, 0, 179, 255)
color4 = rgba(0, 115, 230, 255)
color5 = rgba(79, 153, 0, 255)
color6 = rgba(0, 179, 179, 255)
color7 = rgba(255, 255, 255, 255)
foreground = rgba(0, 0, 0, 255)
