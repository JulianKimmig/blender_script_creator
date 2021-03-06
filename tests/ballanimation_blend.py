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

class NodeSocket(BlenderClass):
    def __init__(self,node_socket,node,number=-1):
        self.number = number
        self.node = node
        self._node_socket=node_socket

    @property
    def socket(self):
        return self._node_socket
    @property
    def name(self):
        return self._node_socket.name

    def __repr__(self):
        return self.name

    @property
    def value(self):
        return self._node_socket.default_value

    @value.setter
    def value(self,v):
        self._node_socket.default_value=v

class Node(BlenderClass):
    dependencies = [NodeSocket]
    node_class = None

    def __init__(self,node,tree=None):
        self._node=node
        self._tree=tree
        self._sockets={}
        self.inputs={}
        self.outputs={}
        name_counter={}
        for i in node.inputs:
            if i.name not in name_counter:
                name_counter[i.name]=[0,0]
            name_counter[i.name][0]+=1

        for i in node.outputs:
            if i.name not in name_counter:
                name_counter[i.name]=[0,0]
            name_counter[i.name][0]+=1

        for n,i in enumerate(node.inputs):
            if name_counter[i.name][0]>1:
                nn="{}_{}".format(i.name,name_counter[i.name][1])
                name_counter[i.name][1]+=1
                i.name=nn
            ns = self.inputs[i.name]=NodeSocket(i,self,number=n)
            #nsp=property(lambda :ns,lambda v:ns.set_default(v))
            setattr(self,ns.name,ns)
        for n,i in enumerate(node.outputs):
            if name_counter[i.name][0]>1:
                nn="{}_{}".format(i.name,name_counter[i.name][1])
                name_counter[i.name][1]+=1
                i.name=nn
            ns = self.outputs[i.name]=NodeSocket(i,self,number=n)
            #nsp=property(lambda :ns,lambda v:ns.set_default(v))
            setattr(self,ns.name,ns)

    @property
    def tree(self):
        return self._tree

    @property
    def name(self):
        return self._node.name

    def __repr__(self):
        return "{}({},{})".format(self.__class__.__name__,self.inputs,self.outputs)

class MaterialShader(Node):
    pass

class GeneralShader(MaterialShader):
    pass

class OutputMaterial(MaterialShader):
    pass

class MixShader(MaterialShader):
    pass

def cast_material_node(node,tree=None):
    if node.__class__ == bpy.types.ShaderNodeOutputMaterial:
        return OutputMaterial(node,tree)
    else:
        return GeneralShader(node,tree)

class Material(BlenderClass):
    dependencies = [cast_material_node]
    materials={}
    def __init__(self, mat):
        self._nodes = {}
        self._mat=mat
        self._mat.use_nodes = True
        self.materials[mat.name]=self
        self._detect_nodes()

    def copy(self):
        return Material(self.mat.copy())

    def get_or_copy(self,name):
        nn = find_material(name)
        if nn is None:
            nn=self.copy()
        nn.name=name
        return nn

    @property
    def name(self):
        return self._mat.name

    @name.setter
    def name(self,name):
        if self.name==name and self.materials[name]==self:
            return
        if name in self.materials:
            raise ValueError("Material with name '{}' already defined".format(name))
        del self.materials[self.name]
        self._mat.name=name
        self.materials[self.name]=self

    @property
    def mat(self):
        return self._mat

    @property
    def nodes(self):
        return self._nodes

    def _detect_nodes(self):
        for node in self.mat.node_tree.nodes:
            if node.name not in self.nodes:
                self.nodes[node.name] = cast_material_node(node,self.mat.node_tree)

    def new_node(self,type="ShaderNodeBsdfPrincipled",name=None):
        if name is None:
            i=0
            while "{}_{}".format(type,i) in self.nodes:
                i+=1
            name="{}_{}".format(type,i)
        if name in self.nodes:
            raise ValueError("Node with name '{}' already defined".format(name))
        nn = self._mat.node_tree.nodes.new(type)
        if name:
            nn.name = name
        self._detect_nodes()
        return self.nodes[name]

    def get_node(self,name):
        return self.nodes.get(name)

    def get_or_create_node(self,name,type="ShaderNodeBsdfPrincipled"):
        nn = self.get_node(name)
        if nn is None:
            nn = self.new_node(type=type,name=name)
        return nn

    def connect(self,node_socket1,node_socket2):
        self._mat.node_tree.links.new(node_socket1.socket,node_socket2.socket)

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
            if self._obj.data.materials[0] != mat.mat:
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
    dependencies = [Material,BlenderObject]
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

    def frames_to_seconds(self,f):
        return f/self._fps

    def go_to_second(self, s):
        self.go_to_frame(self.seconds_to_frames(s))

    def run_seconds(self, s):
        self.run_frames(self.seconds_to_frames(s))

    def finish_animation(self):
        bpy.context.scene.frame_end = self._max_frame

    def clear_all(self):
        for a in bpy.data.actions:
            bpy.data.actions.remove(a)

    def performe_keyframe_op(self,obj,data_path,frames,reverse=False,interpolation=None):
        kf = obj.keyframe_insert(data_path=data_path, frame=self.current_frame)
        print(kf,self.current_frame,obj)

        if interpolation is not None:
            action = obj.animation_data.action
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

    def get_animation_data(self,obj):
        if isinstance(obj,Material):
            return obj.mat.node_tree.animation_data
        elif isinstance(obj,BlenderObject):
            return obj.obj.animation_data
        else:
            return obj.animation_data

    def delete_all_after_frame(self,obj,frame):
        anim=self.get_animation_data(obj)
        if anim is None:
            return
        action= anim.action
        if action is None:
            return
        fcurves = [fc for fc in action.fcurves]
        for fc in fcurves:
            for kfp in list(fc.keyframe_points):
                if kfp.co.x > frame:
#                    action.fcurves.remove(fc)
 #                   break
                    fc.keyframe_points.remove(kfp)


    def change_node_value(self,socket,value,time=0,reverse=False,interpolation=None):
        node=socket.node
        cb = self.performe_keyframe_op(socket.socket,"default_value",frames=self.seconds_to_frames(time),reverse=reverse,interpolation=None)
        socket.value=value
        cb()

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
MAX_SPEED=10
FPS=24
TIME=50
SEED=100
BLINK_TIME=1
np.random.seed(SEED)
anim = BlenderAnimationTracker(fps=FPS)
anim.clear_all()
all_balls = []
base_mat= get_or_create_material(name="ball_base_mat",)
mout=base_mat.get_node("Material Output")
mixer = base_mat.get_or_create_node(name="mixer1",type="ShaderNodeMixShader")
base_mat.connect(mixer.Shader_2,mout.Surface)
mixer.Fac.value = 1
em = base_mat.get_or_create_node(name="emission",type="ShaderNodeEmission")
base_mat.connect(em.Emission,mixer.Shader_0)
glass = base_mat.get_or_create_node(name="glass",type="ShaderNodeBsdfGlass")
base_mat.connect(glass.BSDF,mixer.Shader_1)
rgb = base_mat.get_or_create_node(name="rgb",type="ShaderNodeRGB")
rgb.Color.value=(0,0.7,1,1)
base_mat.connect(rgb.Color,glass.Color)
for i in range(NBALLS):
    ball = get_or_create_object("ball{}".format(i), create_sphere)
    ball.material = base_mat.get_or_copy("ball{}_mat".format(i))
    all_balls.append(ball)
delete_all_but(all_balls)
for ball in all_balls:
    anim.delete_all_after_frame(ball,0)
    #ball.obj.animation_data_clear()
    ball.location = np.random.random(3)*CUBE
    #anim.go_to_frame(1)
speed=(np.random.random(3*NBALLS)-0.5).reshape(3,-1)
speed = speed/np.linalg.norm(speed,axis=0)
speed=(MAX_SPEED*np.random.random(NBALLS))*(speed)
speed = speed.T
pos=[ball.location for ball in all_balls]
for i,ball in enumerate(all_balls):
    anim.go_to_frame(0)
    anim.move_object(ball,*pos[i],interpolation="LINEAR")
    anim.change_node_value(ball.material.get_node("mixer1").Fac,1.0,time=0)
anim.go_to_frame(0)
store_scene("ini")
print("POST INI")
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
last_p=[None for ball in all_balls]
for f in range(TIME*FPS):
    next_locs = pos + speed/FPS
    #wo=False
    for i in range(len(next_locs)):
        while is_out(next_locs[i]):
            anim.move_object(all_balls[i],*pos[i],interpolation="LINEAR")
            next_locs[i], speed[i] = reenter(next_locs[i], speed[i])
            cf=anim.current_frame
            if last_p[i] is not None:
                d=anim.frames_to_seconds(f-last_p[i])
                if d < BLINK_TIME:
                    anim.go_to_frame(cf-1)
                    anim.change_node_value(all_balls[i].material.get_node("mixer1").Fac,
                                           1-(0.5*d/BLINK_TIME),
                                           time=0.00)
                    anim.go_to_frame(cf)
            anim.change_node_value(all_balls[i].material.get_node("mixer1").Fac,0.5,time=0.001,)
            anim.delete_all_after_frame(all_balls[i].material,anim.current_frame)
            anim.change_node_value(all_balls[i].material.get_node("mixer1").Fac,1,time=BLINK_TIME,)
            anim.go_to_frame(cf)
            last_p[i]=cf
            wo=True
    #if wo:
    #    break
    pos = next_locs
    anim.run_frames(1)
for i,ball in enumerate(all_balls):
    anim.move_object(ball,*pos[i],interpolation="LINEAR")
anim.finish_animation()
print('DONE')