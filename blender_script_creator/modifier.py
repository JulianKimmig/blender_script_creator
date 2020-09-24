from blender_script_creator.script import blender_function, blender_basic_script, BlenderClass


class Modifier(BlenderClass):
    tag = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def apply(self, obj, name):
        mod = obj.modifiers.new(name, self.tag)
        for k, v in self.kwargs.items():
            setattr(mod, k, v)


class Subsurface(Modifier):
    tag = 'SUBSURF'
