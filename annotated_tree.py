
class AnnotatedNode(object):
    def __init__(self, underlying_node, annotation, children):
        self.underlying_node = underlying_node
        self.annotation = annotation
        self.children = children
