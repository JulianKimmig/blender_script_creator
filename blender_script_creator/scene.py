import bpy

from blender_script_creator.geometry import BlenderObject
from blender_script_creator.script import blender_function, blender_basic_script


@blender_function(dependencies=[BlenderObject])
def delete_all_but(l):
    obj_list = []
    for i in l:
        if isinstance(i,BlenderObject):
            obj_list.append(i.obj)
        else:
            obj_list.append(l)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj not in obj_list:
            #bpy.data.objects.remove(obj)
            obj.select_set(True)
    bpy.ops.object.delete()

@blender_function(dependencies=[BlenderObject])
def store_scene(name):
    for n,obj in BlenderObject.objects.items():
        obj.store_scene(name)