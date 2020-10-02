from blender_script_creator import bpy
from blender_script_creator.animation import BlenderAnimationTracker, new_camera
from blender_script_creator.geometry import create_sphere, get_or_create_object, connect_points, create_plain_object, \
    BlenderObject
from blender_script_creator.materials import new_material, get_or_create_material, MixShader
from blender_script_creator.modifier import Wave, Subsurface
from blender_script_creator.nodes import Node, connect_node_sockets
from blender_script_creator.scene import delete_all_but, store_scene
from blender_script_creator.script import BlenderScript, blender_function

import numpy as np

script = BlenderScript()


@blender_function(dependencies=[Node, new_camera, connect_node_sockets, connect_points, Wave, BlenderAnimationTracker,
                                delete_all_but, get_or_create_material, Subsurface, BlenderObject])
def beam_main():
    # scene
    RENDER_EDIT = False

    if RENDER_EDIT:
        bpy.context.scene.eevee.use_gtao = True
        bpy.context.scene.eevee.gtao_distance = 1
        bpy.context.scene.eevee.gtao_factor = 3

        bpy.context.scene.eevee.use_bloom = True
        bpy.context.scene.eevee.use_ssr = True

        bpy.context.scene.view_settings.look = 'Very High Contrast'

    bpy.context.scene.use_nodes = True
    ntree = bpy.context.scene.node_tree
    for currentNode in ntree.nodes:
        ntree.nodes.remove(currentNode)

    tree = bpy.context.scene.node_tree
    rlayer_node = Node(tree.nodes.new("CompositorNodeRLayers"), tree)
    composite_node = Node(tree.nodes.new("CompositorNodeComposite"), tree)
    node_viewer_node = Node(tree.nodes.new("CompositorNodeViewer"), tree)
    glare_node = Node(tree.nodes.new("CompositorNodeGlare"), tree)
    connect_node_sockets(tree, rlayer_node.Image, glare_node.Image_0)

    connect_node_sockets(tree, glare_node.Image_1, composite_node.Image)
    connect_node_sockets(tree, glare_node.Image_1, node_viewer_node.Image)

    glare_node.node.glare_type = 'FOG_GLOW'
    glare_node.node.threshold = 0.2

    # ibjects

    delete_all_but()

    anim = BlenderAnimationTracker()
    anim.clear_all()

    class BeamLayer():
        def __init__(self, beam, name):
            self.beam = beam
            self.name = name
            self._ini()
            self._reload_from_beam()


            # self.create(dia=dia,color=color,trans_dens=trans_dens,wave_height=wave_height)

        def _ini(self):
            self._beam_layer = get_or_create_object(self.name,
                                                    connect_points,
                                                    p1=(0, 0, 0),
                                                    p2=(0, 0, 10),
                                                    d=1
                                                    )
            self._beam_layer.parent = self.beam.obj
            self._beam_layer.add_modifier('subsurf', Subsurface(levels=3, render_levels=3))
            self._wave_mod = self._beam_layer.add_modifier('wave', Wave())

          #bpy.context.scene.tool_settings.use_transform_data_origin = True
          #  self._beam_layer.obj.select_set(True)
          #  bpy.ops.transform.rotate(value=np.pi / 2, orient_axis='Z', orient_type='VIEW',
            #                         orient_matrix=((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
           #                          orient_matrix_type='VIEW', mirror=True, use_proportional_edit=False,
           #                          proportional_edit_falloff='SMOOTH', proportional_size=1,
           #                          use_proportional_connected=False, use_proportional_projected=False
           #                          )

            #bpy.context.scene.tool_settings.use_transform_data_origin = False
            self._wave_mod.use_normal = True

            self._wave_mod.narrowness = 0.5
            self._wave_mod.width = 3
            self._wave_mod.height = 0.5

            self._beam_layer_mat = get_or_create_material(name=self.name + "material", )
            self._beam_layer_mat.mat.blend_method = 'BLEND'
            self._beam_layer_mat.mat.shadow_method = 'NONE'
            mout = self._beam_layer_mat.get_node("Material Output")

            mixer = self._beam_layer_mat.get_or_create_node(name="mixer1", type="ShaderNodeMixShader")
            mixer.Shader_2 = mout.Surface
            mixer.Fac.value = 0.5

            self._em = self._beam_layer_mat.get_or_create_node(name="emission", type="ShaderNodeEmission")

            self._em.Strength = 10
            mixer.Shader_1 = self._em.Emission

            trans = self._beam_layer_mat.get_or_create_node(name="transparent", type="ShaderNodeBsdfTransparent")
            mixer.Shader_0 = trans.BSDF

            self._rgbramp = self._beam_layer_mat.get_or_create_node(name="rgbramp", type="ShaderNodeValToRGB")
            self._rgbramp.node.color_ramp.elements[0].position = 0.5

            mixer.Fac = self._rgbramp.Color

            noisetexture = self._beam_layer_mat.get_or_create_node(name="noisetexture", type="ShaderNodeTexNoise")
            noisetexture.Scale = 1.5
            noisetexture.Detail = 16
            noisetexture.Roughness = 0.4
            noisetexture.Distortion = 0.5
            self._rgbramp.Fac = noisetexture.Color

            self._mapping = self._beam_layer_mat.get_or_create_node(name="mapping", type="ShaderNodeMapping")
            noisetexture.Vector = self._mapping.Vector_1

            textcoord = self._beam_layer_mat.get_or_create_node(name="textcoord", type="ShaderNodeTexCoord")
            self._mapping.Vector_0 = textcoord.Object

            self._mapping.Location = (0, 0, 0)
            self._beam_layer.material = self._beam_layer_mat

        def set_color(self, color):
            self._em.Color = color

        def set_dia(self,dia):
            self._beam_layer.dia=dia

        def wave_height(self,wvh):
            self._wave_mod.height = wvh

        def set_trans_dens(self, trans_dens):
            self._rgbramp.node.color_ramp.elements[0].position = trans_dens

        def _set_speed(self):
            l = self.length
            self._wave_mod.speed = self.beam.speed
            self._wave_mod.time_offset = -(l - self._wave_mod.start_position_x) / self.beam.speed

        def _reload_from_beam(self):
            self._set_length(self.beam.length)
            self._set_speed()

        @property
        def length(self):
            return np.linalg.norm(self._beam_layer.end)

        def _set_length(self, l):
            self._beam_layer.end = (l, 0, 0)
            l = self.length
            self._wave_mod.start_position_x = - l
            self._wave_mod.time_offset = -(l - self._wave_mod.start_position_x) / self.beam.speed

        def create_motion(self, animator):
            cf = animator.current_frame
            animator.go_to_frame(0)
            animator.change_node_value(self._mapping.Location, value=(0, 0, 0))
            animator.change_node_value(self._mapping.Rotation, value=(0, 0, 0))
            animator.go_to_frame(animator.max_frame)
            animator.change_node_value(self._mapping.Location, value=(-animator.max_frame * self._wave_mod.speed,0,0, ))
            animator.change_node_value(self._mapping.Rotation, value=(animator.max_frame * 0.1,0,0, ))
            animator.go_to_frame(cf)

    class Beam(BlenderObject):
        def __init__(self, obj, name, start=(0, 0, 0), end=(0, 0, 50), speed=0.25):
            self._layer = []
            super().__init__(obj, name)
            self.speed = speed
            self.name = name
            self._end = np.array(end)
            self._start = np.array(start)

        def add_layer(self, dia=1., color=(0, 0.7, 1, 1), trans_dens=0.52, wave_height=0.5):
            l = BeamLayer(self, name="{}_layer_{}".format(self.name, len(self._layer)),
                          #trans_dens=trans_dens,
                          )
            l.wave_height(wave_height)
            l.set_trans_dens(trans_dens)
            l.set_dia(dia)
            l.set_color(color)
            self._layer.append(l)

        def create_motion(self, animator):
            for layer in self._layer:
                layer.create_motion(animator)

        @property
        def length(self):
            return np.linalg.norm(self.end - self.start)

        @property
        def start(self):
            return self._start

        @property
        def end(self):
            return self._end

        @start.setter
        def start(self, loc):
            loc = np.array(loc)
            l = np.linalg.norm(self.end - loc)
            for lay in self._layer:
                lay.length = l
            self.set_location(*loc)
            self._start = loc
            self._calc_rot()

        @end.setter
        def end(self, loc):
            loc = np.array(loc)
            d_vec=self.start - loc
            l = np.linalg.norm(d_vec)

            for lay in self._layer:
                lay._set_length(l)
            self._end = loc
            self._calc_rot()

        def _calc_rot(self):
            d_vec= self.end - self.start

            def rotation_matrix_from_vectors(vec1, vec2):
                a, b = (vec1 / np.linalg.norm(vec1)).reshape(3), (vec2 / np.linalg.norm(vec2)).reshape(3)
                v = np.cross(a, b)
                c = np.dot(a, b)
                s = np.linalg.norm(v)

                kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
                rotation_matrix = np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c) / (s ** 2))
                return np.nan_to_num(rotation_matrix)

            a=d_vec
            b=np.array([np.linalg.norm(a),0,0])
            a, b = (a / np.linalg.norm(a)).reshape(3), (b / np.linalg.norm(b)).reshape(3)
            if np.all(a == b):
                return self.set_rotation(0,0,0)
            if np.all(a == -b):
                return self.set_rotation(0,0,180)

            R=rotation_matrix_from_vectors(a,b)
            Rx=np.degrees(np.arctan2(R[2,1],R[2,2]))
            Ry=-np.degrees(np.arctan2(-R[2,0],np.sqrt(R[2,1]**2+R[2,2]**2)))
            Rz=-np.degrees(np.arctan2(R[1,0],R[0,0]))

            return self.set_rotation(Rx,Ry,Rz)



    def create_beam(name):
        obj = create_plain_object(name=name,data=bpy.data.meshes.new(name))
        return Beam.from_blender_object(obj)

    beam1 = get_or_create_object("beam1", creator=create_beam, cls=Beam)
    beam1.start = (0, 0,0)
    #beam1=Beam(name="beam1",end=(0,50,0),speed=1)
    beam1.add_layer(color=(1, 0, 0, 1))

    beam1.add_layer(dia=0.4,color=(1,1,1,1),trans_dens=0.48,wave_height=0.2)
    beam1.add_layer(dia=1.75,color=(0.5,0,0.25,1),trans_dens=0.56)

    beam1.end = (-100,0,0)
    anim.go_to_frame(200)

    cam = new_camera(location=(8, 0, 12), rotation_euler=(90, 0, 90))

    # anim.change_node_value(mapping.Location,value=(-anim.max_frame*mod.speed,0,0))

    beam1.create_motion(anim)
    anim.finish_animation()


script.main = beam_main

with open(__file__.replace(".py", "_blend.py"), "w+") as f:
    f.write(script.to_script())

import os

d = '''
import sys
sys.path.append('{}')
import importlib
import {} as blenderscript
import importlib
importlib.reload(blenderscript)
'''.format(
    os.path.dirname(__file__.replace(".py", "_blend.py")),
    os.path.basename(__file__.replace(".py", "_blend.py")).replace(".py", "")
)

print(d)
