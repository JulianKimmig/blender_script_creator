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
        return mod

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

    @property
    def node(self):
        return self._node

    def __setattr__(self, key, value):
        pre=getattr(self,key,None)
        if isinstance(pre,NodeSocket):
            if isinstance(value,NodeSocket):
                connect_node_sockets(self.tree,value,pre)
            else:
                pre.value=value
        else:
            super().__setattr__(key,value)

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

def connect_node_sockets(tree, node_socket1, node_socket2):
    tree.links.new(node_socket1.socket,node_socket2.socket)

class Material(BlenderClass):
    dependencies = [cast_material_node, connect_node_sockets]
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
        connect_node_sockets(self._mat.node_tree, node_socket1, node_socket2)

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
    return bo

class Camera(BlenderObject):
    def set_active_cam(self):
        bpy.context.scene.camera = self.obj

def new_camera(location=(0,0,12),rotation_euler=(0,0,0),lens=18,name="camera"):
    scn = bpy.context.scene
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam = Camera.from_blender_object(create_plain_object(name, cam_data))
    cam.set_location(*location)
    cam.set_rotation(*rotation_euler)
    cam.set_active_cam()
    return cam

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

class Wave(Modifier):
    tag = 'WAVE'

class BlenderAnimationTracker(BlenderClass):
    dependencies = [Material,BlenderObject]
    def __init__(self, fps=24):
        self.current_frame = 0
        self._max_frame = 0
        self._fps = fps

    @property
    def max_frame(self):
        return self._max_frame

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

    def performe_keyframe_op(self,obj,data_path,frames=0,reverse=False,interpolation=None):
        kf = obj.keyframe_insert(data_path=data_path, frame=self.current_frame)

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

    def rotate_object(self,obj,x=0,y=0,z=0,delta=False,animator=None,time=0,reverse=False,interpolation=None):
        if isinstance(obj,BlenderObject):
            obj=obj.obj
        kfcb = self.performe_keyframe_op(obj,"rotation_euler",frames=self.seconds_to_frames(time),reverse=reverse,interpolation=interpolation)
        vec = np.array([x,y,z],dtype=float)*2*np.pi/360
        curr_rot =  np.array(obj.rotation_euler,dtype=float)
        if delta:
            obj.rotation_euler = curr_rot + vec
            delta =  vec
        else:
            obj.rotation_euler = vec
            delta =  np.array(obj.rotation_euler)-curr_rot

        kfcb()


        return delta*360/(2*np.pi)

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

def delete_all_but(l=[]):
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

class Subsurface(Modifier):
    tag = 'SUBSURF'

#OBJETCS
#scene
RENDER_EDIT=False
if RENDER_EDIT:
    bpy.context.scene.eevee.use_gtao = True
    bpy.context.scene.eevee.gtao_distance= 1
    bpy.context.scene.eevee.gtao_factor = 3
    bpy.context.scene.eevee.use_bloom = True
    bpy.context.scene.eevee.use_ssr = True
    bpy.context.scene.view_settings.look = 'Very High Contrast'
bpy.context.scene.use_nodes = True
ntree=bpy.context.scene.node_tree
for currentNode in ntree.nodes:
    ntree.nodes.remove(currentNode)
tree = bpy.context.scene.node_tree
rlayer_node = Node(tree.nodes.new("CompositorNodeRLayers"),tree)
composite_node = Node(tree.nodes.new("CompositorNodeComposite"),tree)
node_viewer_node = Node(tree.nodes.new("CompositorNodeViewer"),tree)
glare_node = Node(tree.nodes.new("CompositorNodeGlare"),tree)
connect_node_sockets(tree,rlayer_node.Image,glare_node.Image_0)
connect_node_sockets(tree,glare_node.Image_1,composite_node.Image)
connect_node_sockets(tree,glare_node.Image_1,node_viewer_node.Image)
glare_node.node.glare_type = 'FOG_GLOW'
glare_node.node.threshold = 0.2
#ibjects
delete_all_but()
anim = BlenderAnimationTracker()
anim.clear_all()
class BeamLayer():
    def __init__(self,beam,name,dia=1.,color=(0,0.7,1,1),trans_dens=0.52,wave_height=0.5):
        self.beam = beam
        self.name = name
        self.create(dia=dia,color=color,trans_dens=trans_dens,wave_height=wave_height)
    def create(self,dia,color,trans_dens,wave_height):
        height=np.linalg.norm(self.beam.end-self.beam.start)
        self._beam_layer = get_or_create_object(self.name,
                                     connect_points,
                                     p1=(0,0,0),
                                     p2=(0,0,height),
                                    d=dia
                                     )
        self._beam_layer.parent = self.beam.obj
        self._beam_layer.add_modifier('subsurf', Subsurface(levels=3, render_levels=3))
        self._wave_mod = self._beam_layer.add_modifier('wave', Wave())
        bpy.context.scene.tool_settings.use_transform_data_origin = True
        self._beam_layer.obj.select_set(True)
        bpy.ops.transform.rotate(value=np.pi/2, orient_axis='Z', orient_type='VIEW',
                                 orient_matrix=((-1, 0, 0), (0,0, 1), (0, 1,0)),
                                 orient_matrix_type='VIEW', mirror=True, use_proportional_edit=False,
                                 proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False
                                 )
        bpy.context.scene.tool_settings.use_transform_data_origin = False
        self._wave_mod.use_normal = True
        self._wave_mod.start_position_x = -height
        self._wave_mod.speed=self.beam.speed
        self._wave_mod.time_offset=-(height-self._wave_mod.start_position_x)/self._wave_mod.speed
        self._wave_mod.narrowness = 0.5
        self._wave_mod.width = 3
        self._wave_mod.height = wave_height
        self._beam_layer_mat = get_or_create_material(name=self.name+"material",)
        self._beam_layer_mat.mat.blend_method = 'BLEND'
        self._beam_layer_mat.mat.shadow_method = 'NONE'
        mout=self._beam_layer_mat.get_node("Material Output")
        mixer = self._beam_layer_mat.get_or_create_node(name="mixer1",type="ShaderNodeMixShader")
        mixer.Shader_2 = mout.Surface
        mixer.Fac.value = 0.5
        em = self._beam_layer_mat.get_or_create_node(name="emission",type="ShaderNodeEmission")
        em.Color=color
        em.Strength=10
        mixer.Shader_1 = em.Emission
        trans = self._beam_layer_mat.get_or_create_node(name="transparent",type="ShaderNodeBsdfTransparent")
        mixer.Shader_0 = trans.BSDF
        rgbramp = self._beam_layer_mat.get_or_create_node(name="rgbramp",type="ShaderNodeValToRGB")
        rgbramp.node.color_ramp.elements[0].position = trans_dens
        mixer.Fac=rgbramp.Color
        noisetexture = self._beam_layer_mat.get_or_create_node(name="noisetexture",type="ShaderNodeTexNoise")
        noisetexture.Scale = 1.5
        noisetexture.Detail = 16
        noisetexture.Roughness = 0.4
        noisetexture.Distortion = 0.5
        rgbramp.Fac = noisetexture.Color
        self._mapping = self._beam_layer_mat.get_or_create_node(name="mapping",type="ShaderNodeMapping")
        noisetexture.Vector = self._mapping.Vector_1
        textcoord = self._beam_layer_mat.get_or_create_node(name="textcoord",type="ShaderNodeTexCoord")
        self._mapping.Vector_0 = textcoord.Object
        self._mapping.Location=(0,0,0)
        self._beam_layer.material=self._beam_layer_mat
    def create_motion(self,animator):
        cf=animator.current_frame
        animator.go_to_frame(0)
        animator.change_node_value(self._mapping.Location,value=(0,0,0))
        animator.go_to_frame(animator.max_frame)
        animator.change_node_value(self._mapping.Location,value=(-animator.max_frame*self._wave_mod.speed,0,0))
        animator.go_to_frame(cf)
class Beam():
    def __init__(self,name,start=(0,0,0),end=(0,0,50),speed=0.25):
        self.speed = speed
        self.name = name
        self.end = np.array(end)
        self.start = np.array(start)
        self._layer=[]
        self.obj=get_or_create_object(self.name,create_plain_object)
    def add_layer(self,dia=1.,color=(0,0.7,1,1),trans_dens=0.52,wave_height=0.5):
        l=BeamLayer(self,name="{}_layer_{}".format(self.name,len(self._layer)),
        dia=dia,color=color,
                    trans_dens=trans_dens,
                    wave_height=wave_height
                    )
        self._layer.append(l)
    def create_motion(self,animator):
        for layer in self._layer:
            layer.create_motion(animator)
beam1=Beam(name="beam1",end=(0,50,0),speed=1)
beam1.add_layer()
beam1.add_layer(dia=0.4,color=(1,1,1,1),trans_dens=0.48,wave_height=0.2)
beam1.add_layer(dia=1.75,color=(1,0,0,1),trans_dens=0.56)
anim.go_to_frame(50)
cam = new_camera(location=(8,0,12),rotation_euler=(90,0,90))
#anim.change_node_value(mapping.Location,value=(-anim.max_frame*mod.speed,0,0))
beam1.create_motion(anim)
anim.finish_animation()
print('DONE')