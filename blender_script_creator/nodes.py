from blender_script_creator.script import BlenderClass, blender_function


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
        return self._node_socket.name.replace(" ","_")

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


@blender_function(dependencies=[])
def connect_node_sockets(tree, node_socket1, node_socket2):
    tree.links.new(node_socket1.socket,node_socket2.socket)
