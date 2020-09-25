from blender_script_creator import bpy
from blender_script_creator.script import BlenderClass, blender_function


class MaterialShader(BlenderClass):
    pass
class MixShader(MaterialShader):
    pass


def cast_material_node(node):
    pass


class Material(BlenderClass):
    dependencies = [cast_material_node]
    materials={}
    def __init__(self, mat):
        self._nodes = {}
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
        return self._nodes

    def _detect_nodes(self):
        for node in self.mat.node_tree.nodes:
            if node.name in self.nodes:
                self.nodes[node.name] = cast_material_node(node)




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