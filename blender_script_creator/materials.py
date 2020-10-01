from blender_script_creator import bpy
from blender_script_creator.nodes import Node, connect_node_sockets
from blender_script_creator.script import BlenderClass, blender_function


class MaterialShader(Node):
    pass

class MixShader(MaterialShader):
    pass

class OutputMaterial(MaterialShader):
    pass

class GeneralShader(MaterialShader):
    pass


@blender_function(dependencies=[GeneralShader,OutputMaterial,MixShader])
def cast_material_node(node,tree=None):
    if node.__class__ == bpy.types.ShaderNodeOutputMaterial:
        return OutputMaterial(node,tree)
    else:
        return GeneralShader(node,tree)

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

@blender_function(dependencies=[Material])
def new_material(name):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    node_tree = mat.node_tree
    nodes = node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    nodes.remove(bsdf)
    return Material(mat)

@blender_function(dependencies=[Material])
def find_material(name):
    if name in Material.materials:
        return Material.materials[name]
    for obj in bpy.data.materials:
        if obj.name == name:
            return Material(obj)

    for obj in bpy.data.materials:
        if obj.name.rsplit(".", maxsplit=1)[0] == name:
            return Material(obj)

@blender_function(dependencies=[find_material,new_material])
def get_or_create_material(name):
    obj = find_material(name)
    if obj is None:
        obj = new_material(name)
    return obj