
# TODO: There is a place for plugin to choose current context
import Houdini
# from hafarm import Houdini
reload(Houdini)
from Houdini import HaContextHoudini

from HaGraph import HaGraphItem

def plugin_property_(func):
    def wrapper_property_(instance, *args, **kwargs):
        context_class = instance.context_class
        private_attribute_name = '_%s' % func.__name__
        if hasattr(context_class, private_attribute_name) == False:
            raise Exception('%s has no "%s". You have to implement it' % (context_class, private_attribute_name))
        func_ = context_class.__getattribute__(private_attribute_name)
        return func_(*args, **kwargs) 
    return wrapper_property_        


class HaContext(object):
    context_class = HaContextHoudini()
    def __init__(self, external_hashes=[]):
        HaGraphItem._external_hashes = (lambda: [(yield x) for x in external_hashes ])()

    @plugin_property_
    def get_graph(self, **kwargs):
        pass

