from warnings import warn

try:
    import bmesh as blendermesh
    import bpy as blenderpy
except ModuleNotFoundError:
    warn("blender libraries cannot be imported, the script creator should work but autocomplete might not!")
    blendermesh = None
    blenderpy = None

bmesh = blendermesh
bpy = blenderpy