from blender_script_creator import bpy, bmesh
from blender_script_creator.materials import Material
from blender_script_creator.modifier import Subsurface, Modifier
from blender_script_creator.script import blender_function, blender_basic_script, BlenderClass

import numpy as np


#@blender_function(dependencies=[Modifier])
class BlenderObject(BlenderClass):
    dependencies=BlenderClass.dependencies+[Modifier,Material]
    used_names = []
    objects = {}

    def __init__(self, obj, name):
        self._material=None
        self._obj = obj
        self.scenes = {}
        if name in self.used_names:
            raise ValueError("object with name '{}' already defined, please rename".format(name))
        self.used_names.append(name)
        self.objects[name] = self
        self._true_name = obj.name
        self.name=name

    @property
    def obj(self):
        return self._obj

    def add_modifier(self, name, mod: Modifier):
        return mod.apply(self._obj, name)

    @property
    def parent(self):
        return self._obj.parent

    @parent.setter
    def parent(self,obj):
        if isinstance(obj,BlenderObject):
            obj=obj.obj
        self._obj.parent=obj

    @property
    def location(self):
        return np.array(self._obj.location)

    @location.setter
    def location(self, xyz):
        x, y, z = xyz
        self.set_location(x, y, z)

    def set_location(self, x=None, y=None, z=None):
        if x is None or y is None or z is None:
            l = self.location
            if x is None:
                x = l[0]
            if y is None:
                y = l[1]
            if z is None:
                z = l[2]
        self._obj.location = (x, y, z)

    def set_rotation(self, x=None, y=None, z=None):
        fac=(2*np.pi/360)
        rv=np.array([x,y,z],dtype=float)
        rv=rv*fac
        if x is None or y is None or z is None:
            l = self._obj.rotation_euler
            if x is None:
                rv[0] = l[0]
            if y is None:
                rv[1] = l[1]
            if z is None:
                rv[1] = l[2]

        self._obj.rotation_euler = rv

    def set_true_name(self, name):
        self._true_name = name

    def store_scene(self, scene_n):
        self.scenes[scene_n] = {
            "location": self._obj.location
        }

    @property
    def material(self):
        if self._material is None:
            if self._obj.data.materials:
                self.material=Material(self._obj.data.materials[0])
        return self._material

    @material.setter
    def material(self,mat:Material):
        self._material=mat
        if self._obj.data.materials:
            if self._obj.data.materials[0] != mat.mat:
                self._obj.data.materials[0] = mat.mat
        else:
            self._obj.data.materials.append(mat.mat)

    @classmethod
    def unregister(cls, obj):
        BlenderObject.used_names.remove(obj.name)
        del BlenderObject.objects[obj.name]

    @classmethod
    def from_blender_object(cls,obj):
        BlenderObject.unregister(obj)
        return cls(obj.obj,name=obj.name)

@blender_function(dependencies=[BlenderObject])
def create_plain_object(name, data=None):
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    bo = BlenderObject(obj, name=name)
    return bo


@blender_function(dependencies=[BlenderObject])
def find_object(name):
    if name in BlenderObject.objects:
        return BlenderObject.objects[name]
    for obj in bpy.context.scene.objects:
        if obj.name == name:
            return BlenderObject(obj, name=name)

    for obj in bpy.context.scene.objects:
        if obj.name.rsplit(".", maxsplit=1)[0] == name:
            return BlenderObject(obj, name=name)


@blender_function(dependencies=[find_object])
def get_or_create_object(name, creator, **kwargs):
    obj = find_object(name)
    if obj is None:
        obj = creator(name=name, **kwargs)
    return obj


@blender_function(dependencies=[create_plain_object, Subsurface])
def create_sphere(name="uvsphere", x=0, y=0, z=0, dia=1):
    mesh = bpy.data.meshes.new(name)
    uvsphere = create_plain_object(name, mesh)

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=dia * 2 * 1.162)
    bm.to_mesh(mesh)
    bm.free()

    uvsphere.add_modifier('spherification', Subsurface(levels=3, render_levels=6))

    uvsphere.set_location(x, y, z)

    return uvsphere


@blender_basic_script
def set_parent(child, parent):
    child.parent = parent


@blender_function(dependencies=[create_plain_object])
def create_text(text="lorem", name="font object", x=0, y=0, z=0, size=1):
    font_curve = bpy.data.curves.new(type="FONT", name="Font Curve")
    font_curve.body = text
    text = create_plain_object(name, font_curve)
    text.location = (x, y, z)
    text.data.size = size
    return text


@blender_function(dependencies=[BlenderObject])
def connect_points(p1, p2, d=1, name="cylinder"):
    p1=np.array(p1)
    p2=np.array(p2)
    o = (p1 + p2) / 2
    bpy.ops.curve.primitive_bezier_curve_add()
    curve = bpy.context.object
    curve.name=name

    curve.data.dimensions = '3D'
    curve.data.fill_mode = 'FULL'
    curve.data.bevel_depth = d
    curve.data.bevel_resolution = 6
    # set first point to centre of sphere1
    curve.data.splines[0].bezier_points[0].co = p1 - o
    curve.data.splines[0].bezier_points[0].handle_left_type = 'VECTOR'
    # set second point to centre of sphere2
    curve.data.splines[0].bezier_points[1].co = p2 - o
    curve.data.splines[0].bezier_points[1].handle_left_type = 'VECTOR'
    curve.location = o
    return BlenderObject(curve,name=name)
