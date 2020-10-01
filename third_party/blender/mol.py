import bpy
import rdkit
from rdkit.Chem import AllChem

from molNet.mol.molecules import Molecule
from molNet.third_party.blender.tools import blender_basic_script, blender_function
from molNet.third_party.blender.tools.geometry import create_sphere, create_plain_object, connect_points
from molNet.third_party.blender.tools.groups import to_group
from molNet.third_party.blender.tools.materials import new_material, set_material


@blender_function(dependencies=[new_material])
def default_atom_material(color):
    mat = new_material()
    bsdf = mat.new_node()
    emission = mat.new_node(type="ShaderNodeEmission",name="Emission")
    color_node= mat.new_node(type="ShaderNodeRGB")
    mixer = mat.new_node(type="ShaderNodeMixShader",name="Mixer")

    bsdf.set('Base Color',color)
    color_node.set("Color",color)
    emission.set("Strength",30)
    mixer.set("Fac",1.0)

    mat.connect_node_sockets(color_node.output("Color"), emission.input("Color"))
    mat.connect_node_sockets(color_node.output("Color"), bsdf.input("Base Color"))

    mat.connect_node_sockets(emission.output("Emission"), mixer.input(1))
    mat.connect_node_sockets(bsdf.output("BSDF"), mixer.input(2))

    mat.connect_node_sockets(mixer.output("Shader"), mat.material_output.input("Surface"))
    return mat

@blender_function(dependencies=[default_atom_material])
def get_default_atom_map():
    return {
        "H": {
            "dia": 0.5,
            "material":default_atom_material(color=(1,1,1,1))
        },
        "C": {
            "dia": 1,
            "material":default_atom_material(color=(0.1,0.1,0.1,1))
        },
        "O": {
            "dia": 0.95,
            "material":default_atom_material(color=(1,0,0,1))
        },
        "N": {
            "dia": 0.95,
            "material":default_atom_material(color=(0,0,1,1))
        },
        "Unknown": {
            "dia": 2,
            "material":default_atom_material(color=(0.5,0.5,0.5,1))
        },
    }


@blender_function(dependencies=[create_sphere, to_group, create_plain_object, connect_points, get_default_atom_map,set_material])
def create_molecule(atoms, coordinates, bonds, name, dist=0, bond_size=0.3, atom_map=get_default_atom_map()):
    spheres = []
    mol = create_plain_object(name)
    for i in range(len(atoms)):
        atom = atom_map.get(atoms[i],atom_map.get("Unknown"))
        x, y, z = coordinates[i]
        x, y, z = x * (dist + 1), y * (dist + 1), z * (dist + 1)
        sphere = create_sphere(name="atom_{}".format(i), x=x, y=y, z=z, dia=atom["dia"])
        sphere.parent = mol
        spheres.append(sphere)

        set_material(sphere,atom["material"].material,copy=True)



    connections=[]
    for i,b in enumerate(bonds):
        con = connect_points(
            spheres[b[0]].location,
            spheres[b[1]].location,
            d=bond_size,
        )
        con.name = "bond_{}".format(i)
        con.data.name = "bond_{}".format(i)

        con.parent = mol
        connections.append(con)

    return mol
    # to_group(name,spheres)


def mol_to_model(mol: Molecule, mol_name=None, dist=0,varname=None,seed=None):
    _mol = mol.get_mol()
    AllChem.EmbedMolecule(_mol,randomSeed=-1 if seed is None else seed)
    conf = _mol.GetConformer()
    if mol_name is None:
        mol_name = str(mol)

    if varname is None:
        varname = mol_name

    return create_molecule(
        atoms=[a.GetSymbol() for a in _mol.GetAtoms()],
        coordinates=[list(conf.GetAtomPosition(i)) for i, a in enumerate(_mol.GetAtoms())],
        bonds=[(b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in _mol.GetBonds()],
        name=mol_name,
        dist=dist,
    ).set_varname(varname)
