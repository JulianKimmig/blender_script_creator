from blender_script_creator import bpy
from blender_script_creator.geometry import BlenderObject, create_plain_object
from blender_script_creator.materials import Material
from blender_script_creator.script import blender_function, blender_basic_script
import numpy as np

@blender_function(dependencies=[BlenderObject,Material])
def delete_all_but(l=[]):
    def flatten(ll):
        if isinstance(ll,(list,tuple,np.ndarray)):
            ll=list(ll)
        else:
            return [ll]
        return flatten(ll[0]) + (flatten(ll[1:]) if len(ll) > 1 else [])
    l = list(flatten(l))

    obj_list = []
    def append_blender_object(obj):
        obj_list.append(obj)
        for c in obj.children:
            append_blender_object(c)
        try:
            obj_list.append(obj.data.materials[0])
        except:
            pass

    for i in l:
        if isinstance(i,BlenderObject):
            append_blender_object(i.obj)
            obj_list.append(i.obj)
            if i.material:
                obj_list.append(i.material.mat)
        elif isinstance(i,Material):
            obj_list.append(i.mat)
        else:
            print(i)
            obj_list.append(i)
    obj_list=list(set(obj_list))

    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj not in obj_list:
            obj.select_set(True)
    bpy.ops.object.delete()

    for material in bpy.data.materials:
        if material not in obj_list:
            if material.users == 0:
                bpy.data.materials.remove(material)

    for mesh in bpy.data.meshes:
        if mesh not in obj_list:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)

    for curve in bpy.data.curves:
        if curve not in obj_list:
            if curve.users == 0:
                bpy.data.curves.remove(curve)

@blender_function(dependencies=[BlenderObject])
def store_scene(name):
    for n,obj in BlenderObject.objects.items():
        obj.store_scene(name)


class LightSource(BlenderObject):
    def __init__(self, obj, name,type="POINT",energy=10):
        super().__init__(obj, name)
        self.type = type
        self.energy=energy

    @property
    def type(self):
        return self._obj.data.type

    @type.setter
    def type(self,type):
        self._obj.data.type = type

    @property
    def energy(self):
        return self._obj.data.energy

    @energy.setter
    def energy(self,energy):
        self._obj.data.energy = energy

    @classmethod
    def new(cls,name,type='POINT',**kwargs):
        light_data = bpy.data.lights.new(name=name, type=type)
        light_data.energy = 10
        return LightSource(create_plain_object(name, light_data),name,type=type, **kwargs)
