from warnings import warn

class Anygetter():
    def __init__(self,name,original=None):
        self.name = name
        self._original = original

    def __getattribute__(self, item):
        if item == "_original":
            return super().__getattribute__(item)
        if self._original:
            try:
                d = self._original.__getattribute__(item)
                return Anygetter(item,d)
            except:
                pass
        return Anygetter("__unknown__")

    def __call__(self, *args, **kwargs):
        if self._original:
            try:
                d = self._original(*args, **kwargs)
                return Anygetter("{}({},{})".format(self.name,args,kwargs),d)
            except:
                pass
        return Anygetter("{}({},{})".format(self.name,args,kwargs))

    def __iter__(self):
        return iter([])

    def __getitem__(self, item):
        if self._original:
            try:
                d = self._original.__getitem__(item)
                return Anygetter(item,d)
            except:
                pass
        return Anygetter(item)
try:
    import bmesh as blendermesh
    import bpy as blenderpy
    blendermesh = Anygetter("bmesh",blendermesh)
    blenderpy = Anygetter("bpy",blenderpy)
except ModuleNotFoundError:
    warn("blender libraries cannot be imported, the script creator should work but autocomplete might not!")
    blendermesh = Anygetter("bmesh")
    blenderpy = Anygetter("bpy")

bmesh = blendermesh
bpy = blenderpy