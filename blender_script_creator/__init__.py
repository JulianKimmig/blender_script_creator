from warnings import warn

class Anygetter():
    def __getattribute__(self, item):
        return Anygetter()
try:
    import bmesh as blendermesh
    import bpy as blenderpy
except ModuleNotFoundError:
    warn("blender libraries cannot be imported, the script creator should work but autocomplete might not!")
    blendermesh = Anygetter()
    blenderpy = Anygetter()

bmesh = blendermesh
bpy = blenderpy