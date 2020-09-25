import bpy 
import bmesh 
import numpy as np

class BlenderClass():
    dependencies=[]

class Modifier(BlenderClass):
    tag = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def apply(self, obj, name):
        mod = obj.modifiers.new(name, self.tag)
        for k, v in self.kwargs.items():
            setattr(mod, k, v)

class Material(BlenderClass):
    materials={}
    def __init__(self, mat):
        self._mat=mat
        self._mat.use_nodes = True
        self.materials[mat.name]=self
        self._detect_nodes()

    @property
    def name(self):
        return self._mat.name

    @property
    def mat(self):
        return self._mat

    @property
    def nodes(self):
        return self._mat.node_tree.nodes

    def _detect_nodes(self):
        for node in self.nodes:
            print(node.name)

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
        self._true_name = name

    @property
    def obj(self):
        return self._obj

    def add_modifier(self, name, mod: Modifier):
        mod.apply(self._obj, name)

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
            self._obj.data.materials[0] = mat.mat
        else:
            self._obj.data.materials.append(mat.mat)

def find_object(name):
    if name in BlenderObject.objects:
        return BlenderObject.objects[name]
    for obj in bpy.context.scene.objects:
        if obj.name == name:
            return BlenderObject(obj, name=name)

    for obj in bpy.context.scene.objects:
        if obj.name.rsplit(".", maxsplit=1)[0] == name:
            return BlenderObject(obj, name=name)

def get_or_create_object(name, creator, **kwargs):
    obj = find_object(name)
    if obj is None:
        obj = creator(name=name, **kwargs)
    return obj

def create_plain_object(name, data=None):
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    bo = BlenderObject(obj, name=name)
    bo.set_true_name(obj.name)
    return bo

class Subsurface(Modifier):
    tag = 'SUBSURF'

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

def store_scene(name):
    for n,obj in BlenderObject.objects.items():
        obj.store_scene(name)

class BlenderAnimationTracker(BlenderClass):
    def __init__(self, fps=24):
        self.current_frame = 0
        self._max_frame = 0
        self._fps = fps

    def go_to_frame(self, f):
        self._max_frame = max(self._max_frame, f)
        self.current_frame = f

    def run_frames(self, f):
        self.go_to_frame(self.current_frame + np.ceil(f))

    def seconds_to_frames(self,s):
        return self._fps * s

    def go_to_second(self, s):
        self.go_to_frame(self.seconds_to_frames(s))

    def run_seconds(self, s):
        self.run_frames(self.seconds_to_frames(s))

    def finish_animation(self):
        bpy.context.scene.frame_end = self._max_frame

    def performe_keyframe_op(self,obj,data_path,frames,reverse=False,interpolation=None):
        kf = obj.keyframe_insert(data_path=data_path, frame=self.current_frame)
        action = obj.animation_data.action

        if interpolation is not None:

        #kf.interpolation ="LINEAR"
            fcurves = [fc for fc in action.fcurves if fc.data_path == data_path]
            for fc in fcurves:
                for kfp in fc.keyframe_points:
                    if kfp.co.x == self.current_frame:
                        kfp.interpolation = interpolation
        def compl():
            if reverse:
                f = self.current_frame
            self.run_frames(frames)
            kf = obj.keyframe_insert(data_path=data_path, frame=self.current_frame)
         #   kf.interpolation ="LINEAR"
            if reverse:
                self.go_to_frame(f)
        return compl

    def move_object(self,obj,x=0,y=0,z=0,delta=False,time=0,reverse=False,interpolation=None):
        if isinstance(obj,BlenderObject):
            obj=obj.obj
        kfcb = self.performe_keyframe_op(obj,"location",frames=self.seconds_to_frames(time),reverse=reverse,interpolation=interpolation)

        vec = np.array([x,y,z],dtype=float)
        curr_loc=np.array(obj.location,dtype=float)
        if delta:
            obj.location = curr_loc + vec
            delta =  vec
        else:
            obj.location = vec
            delta =  np.array(obj.location)-curr_loc

        kfcb()

        return delta

def find_material(name):
    if name in Material.materials:
        return Material.materials[name]
    for obj in bpy.data.materials:
        if obj.name == name:
            return Material(obj)

    for obj in bpy.data.materials:
        if obj.name.rsplit(".", maxsplit=1)[0] == name:
            return Material(obj)

def new_material(name):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    node_tree = mat.node_tree
    nodes = node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    nodes.remove(bsdf)
    return Material(mat)

def get_or_create_material(name):
    obj = find_material(name)
    if obj is None:
        obj = new_material(name)
    return obj

#OBJETCS
##init
NBALLS = 10
CUBE=30
MAX_SPEED=100
FPS=24
TIME=1
anim = BlenderAnimationTracker(fps=FPS)
all_balls = []
base_mat= get_or_create_material(name="ball_base_mat")
for i in range(NBALLS):
    ball = get_or_create_object("ball{}".format(i), create_sphere)
    ball.material = base_mat
    all_balls.append(ball)
for ball in all_balls:
    ball.obj.animation_data_clear()
    ball.location = np.random.random(3)*CUBE
delete_all_but(all_balls)
store_scene("ini")
speed=(np.random.random(3*NBALLS)-0.5).reshape(3,-1)
speed = speed/np.linalg.norm(speed,axis=0)
speed=(MAX_SPEED*np.random.random(NBALLS))*(speed)
speed = speed.T
pos=[ball.location for ball in all_balls]
for i,ball in enumerate(all_balls):
    anim.move_object(ball,*pos[i],interpolation="LINEAR")
def is_out(xyz):
    for c in xyz:
        if c < 0 or c > CUBE:
            return True
    return False
def reenter(xyz,speeds):
    for i,c in enumerate(xyz):
        if c < 0:
            xyz[i]=-c
            speeds[i]=-speeds[i]
        if c > CUBE:
            xyz[i]=2*CUBE-c
            speeds[i]=-speeds[i]
    return xyz,speeds
for f in range(TIME*FPS):
    next_locs = pos + speed/FPS
    for i in range(len(next_locs)):
        while is_out(next_locs[i]):
            anim.move_object(all_balls[i],*pos[i],interpolation="LINEAR")
            next_locs[i], speed[i] = reenter(next_locs[i], speed[i])
    pos = next_locs
    anim.run_frames(1)
for i,ball in enumerate(all_balls):
    anim.move_object(ball,*pos[i],interpolation="LINEAR")
anim.finish_animation()
print('DONE')