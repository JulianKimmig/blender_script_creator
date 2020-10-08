from warnings import warn

from blender_script_creator import bpy, bmesh
from blender_script_creator.materials import Material
from blender_script_creator.modifier import Subsurface, Modifier
from blender_script_creator.script import blender_function, blender_basic_script, BlenderClass

import numpy as np


@blender_function(dependencies=[])
def create_plain_object(name, data=None):
    print("NEW OBJECT", name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return obj
    # bo = BlenderObject(obj, name=name)
    # return bo


@blender_function(dependencies=[])
def find_object(name, cls=None,deep_search=False, **kwargs):
    if cls is None:
        cls = BlenderObject

    if name in BlenderObject.objects:
        return BlenderObject.objects[name]
    for obj in bpy.context.scene.objects:
        if obj.name == name:
            return cls(obj, name=name, **kwargs)

    if deep_search:
        for obj in bpy.context.scene.objects:
            if obj.name.rsplit(".", maxsplit=1)[0] == name:
                return cls(obj, name=name, **kwargs)


@blender_function(dependencies=[find_object])
def get_or_create_object(name, creator=None, cls=None, **kwargs):
    if creator is None:
        creator = BlenderObject.new
    if cls is None:
        cls = BlenderObject
    obj = find_object(name, cls=cls, **kwargs)

    if obj is None:
        obj = creator(name=name, **kwargs)
    if not isinstance(obj, cls):
        cls.from_blender_object(obj, **kwargs)
    return obj


class BlenderObject(BlenderClass):
    dependencies = BlenderClass.dependencies + [Modifier, Material, create_plain_object, get_or_create_object]
    used_names = []
    objects = {}

    def __init__(self, obj, name):
        self._material = None
        self._obj = obj
        self.scenes = {}
        if name is None:
            name = obj.name
        if name in self.used_names:
            raise ValueError("object with name '{}' already defined, please rename".format(name))
        self.used_names.append(name)
        self.objects[name] = self
        self._true_name = obj.name
        self.name = name

    @property
    def obj(self):
        return self._obj

    @property
    def modifiers(self):
        return list(self._obj.modifiers)

    def has_modifier(self, name):
        return name in self._obj.modifiers

    def get_modifier(self,name):
        return self._obj.modifiers[name]

    def add_modifier(self, name, mod: Modifier):
        if self.has_modifier(name):
            print("WARNING:","modifier '{}' already set on {}".format(name,self))
            return self.get_modifier(name)
        return mod.apply(self._obj, name)

    def remove_modifier(self,name):
        self._obj.modifiers.remove(name)

    @property
    def parent(self):
        return self._obj.parent

    @parent.setter
    def parent(self, obj):
        if isinstance(obj, BlenderObject):
            obj = obj.obj
        self._obj.parent = obj

    @property
    def location(self):
        return np.array(self._obj.location)

    @location.setter
    def location(self, xyz):
        x, y, z = xyz
        self.set_location(x, y, z)

    @property
    def world_location(self):
        def ploc(obj):
            sloc=np.array(obj.location)
            if obj.parent:
                return ploc(obj.parent)+sloc
            return sloc

        return ploc(self._obj)

    def set_location(self, x=None, y=None, z=None):
        if x is None or y is None or z is None:
            l = self.location
            if x is None:
                x = l[0]
            if y is None:
                y = l[1]
            if z is None:
                z = l[2]

        xyz = np.array([x, y, z])
        if np.allclose(self.location, xyz):
            return
        self._obj.location = xyz

    @property
    def rotation(self):
        return np.array(self._obj.location)

    @rotation.setter
    def rotation(self, xyz):
        x, y, z = xyz
        self.set_rotation(x, y, z)

    def set_rotation(self, x=None, y=None, z=None):

        rv = np.array([x, y, z], dtype=float)
        rv = np.deg2rad(rv)
        if x is None or y is None or z is None:
            l = self._obj.rotation_euler
            if x is None:
                rv[0] = l[0]
            if y is None:
                rv[1] = l[1]
            if z is None:
                rv[1] = l[2]

        self._obj.rotation_euler = rv
        return np.rad2deg(rv)

    def set_true_name(self, name):
        self._true_name = name

    def store_scene(self, scene_n):
        self.scenes[scene_n] = {
            "location": self._obj.location
        }

    @property
    def material(self):
        if self._material is None:
            if self._obj.data is not None:
                if hasattr(self._obj.data, "materials"):
                    if self._obj.data.materials:
                        self.material = Material(self._obj.data.materials[0])
        return self._material

    @material.setter
    def material(self, mat: Material):
        self._material = mat
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
    def delete(cls, obj):
        cls.unregister(obj)
        bpy.ops.object.select_all(action='DESELECT')
        obj._obj.select_set(True)
        bpy.ops.object.delete()

    @classmethod
    def from_blender_object(cls, obj, **kwargs):
        BlenderObject.unregister(obj)
        return cls(obj.obj, name=obj.name, **kwargs)

    @classmethod
    def new(cls, name, **kwargs):
        return cls(create_plain_object(name), name=name, **kwargs)

    @classmethod
    def get_or_create_object(cls, name, **kwargs):
        return get_or_create_object(name, creator=cls.new, cls=cls, **kwargs)




class Sphere(BlenderObject):
    dependencies = BlenderObject.dependencies + [Subsurface]

    def __init__(self, obj, name, dia=1):
        super().__init__(obj, name)

    @classmethod
    def new(cls, name, dia=1):
        mesh = bpy.data.meshes.new(name)
        uvsphere = Sphere(create_plain_object(name, mesh), name=name)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, diameter=dia)
        bm.to_mesh(mesh)
        bm.free()
        uvsphere.add_modifier('spherification', Subsurface(levels=2, render_levels=4))
        return uvsphere


class Connection(BlenderObject):

    def __init__(self, obj, name, p1, p2, d=1,resolution=10):
        super().__init__(obj, name)
        self._resolution = resolution
        self._obj.data.bevel_depth = d
        self.set_start_end(p1, p2)
        self._obj.data.bevel_factor_mapping_start = 'SPLINE'
        self._obj.data.bevel_factor_mapping_end = 'SPLINE'




    @property
    def start(self):
        return np.array(self._obj.location) + np.array(self._obj.data.splines[0].bezier_points[0].co)

    @property
    def length(self):
        return np.linalg.norm(self.end - self.start)

    @property
    def dia(self):
        return self._obj.data.bevel_depth

    @dia.setter
    def dia(self, dia):
        self._obj.data.bevel_depth = dia
        self._obj.data.bevel_resolution = dia*10

    @property
    def end(self):
        return np.array(self._obj.data.splines[0].bezier_points[1].co) + np.array(self._obj.location)

    @start.setter
    def start(self, start):
        self.set_start_end(start, self.end)

    @end.setter
    def end(self, end):
        self.set_start_end(self.start, end)

    def set_start_end(self, start, end):
        start = np.array(start)
        end = np.array(end)
        self._obj.location = (0, 0, 0)
        o = (start + end) / 2

        self._obj.data.splines[0].bezier_points[0].co = start - o
        self._obj.data.splines[0].bezier_points[0].handle_left_type = 'VECTOR'

        self._obj.data.splines[0].bezier_points[1].co = end - o
        self._obj.data.splines[0].bezier_points[1].handle_left_type = 'VECTOR'
        self._obj.location = o

        self._obj.data.resolution_u = self._resolution*self.length


    @classmethod
    def new(cls, name, **kwargs):
        bpy.ops.curve.primitive_bezier_curve_add()
        curve = bpy.context.object
        curve.name = name
        curve.data.dimensions = '3D'
        curve.data.fill_mode = 'FULL'
        c = cls(curve, name=name,**kwargs)
        return c

class BlenderText(BlenderObject):
    def __init__(self, obj, name, text="lorem",size=1,align_x = 'CENTER',align_y = 'CENTER'):
        super().__init__(obj, name)
        self.text = text
        self.size=size
        self.align_x = align_x
        self.align_y = align_y

    @property
    def align_x(self):
        return self.obj.data.align_x

    @align_x.setter
    def align_x(self,alignment):
        self.obj.data.align_x = alignment

    @property
    def align_y(self):
        return self.obj.data.align_y

    @align_y.setter
    def align_y(self,alignment):
        self.obj.data.align_y = alignment

    @property
    def text(self):
        return self.obj.data.body

    @text.setter
    def text(self, text):
        self.obj.data.body = text

    @property
    def size(self):
        return self.obj.data.size

    @size.setter
    def size(self, size):
        self.obj.data.size = size

    @classmethod
    def new(cls, name, **kwargs):
        font_curve = bpy.data.curves.new(type="FONT", name=name)
        text = BlenderText(create_plain_object(name, font_curve),name, **kwargs)
        return text


@blender_function(dependencies=[create_plain_object])
def create_text(text="lorem", name="font object", x=0, y=0, z=0, size=1):
    font_curve = bpy.data.curves.new(type="FONT", name="Font Curve")
    font_curve.body = text
    text = create_plain_object(name, font_curve)
    text.location = (x, y, z)
    text.data.size = size
    raise NotImplementedError()
    return text
