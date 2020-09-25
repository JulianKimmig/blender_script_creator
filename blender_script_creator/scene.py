from blender_script_creator import bpy
from blender_script_creator.geometry import BlenderObject
from blender_script_creator.materials import Material
from blender_script_creator.script import blender_function, blender_basic_script


@blender_function(dependencies=[BlenderObject,Material])
def delete_all_but(l):
    obj_list = []
    for i in l:
        if isinstance(i,BlenderObject):
            obj_list.append(i.obj)
            if i.material:
                obj_list.append(i.material.mat)
        elif isinstance(i,Material):
            obj_list.append(i.mat)
        else:
            print(i)
            obj_list.append(i)
    #print(obj_list)
    obj_list=list(set(obj_list))

    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj not in obj_list:
            obj.select_set(True)
    bpy.ops.object.delete()

    for material in bpy.data.materials:
        if material not in obj_list:
            material.user_clear()
            bpy.data.materials.remove(material)

@blender_function(dependencies=[BlenderObject])
def store_scene(name):
    for n,obj in BlenderObject.objects.items():
        obj.store_scene(name)