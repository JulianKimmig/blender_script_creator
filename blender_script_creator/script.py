import inspect

class BlenderFunction():
    def __init__(self, func, dependencies=None):
        if dependencies is None:
            dependencies = []
        self.dependencies = dependencies
        self._func=func

    @property
    def func(self):
        return self._func

    def __call__(self, *args, **kwargs):
        try:
            return self._func(*args,**kwargs)
        except:
            pass
    def to_code(self):
        m = inspect.getsource(self.func)
        while m.replace(" ","").startswith("@"):
            m = m.split("\n",maxsplit=1)[1]

        return m

    @property
    def __name__(self):
        return self._func.__name__

class _BlenderClass():
    dependencies=[]

    @classmethod
    def to_code(cls):
        m = inspect.getsource(cls)
        while m.replace(" ","").startswith("@"):
            m = m.split("\n",maxsplit=1)[1]
        m = m.replace("_BlenderClass","")
        return m

    def __str__(self):
        return self.__class__.to_code()

class BlenderClass(_BlenderClass):
    dependencies=[]

class BlenderVariable():
    def __init__(self,name,value):
        self.value = value
        self.name = name

    def to_code(self):
        return "{} = {}".format(self.name,self.value)

def blender_function(dependencies=None):
    if dependencies is None:
        dependencies = []

    def wrapper(func):
        bf = BlenderFunction(func,dependencies=dependencies)
        return bf
    return wrapper

def blender_basic_script(func):
    return blender_function(dependencies=None)(func)



class BlenderScript():
    def __init__(self):
        self._blender_variables = []
        self._needed_objects = []
        self._blender_functions = []
        self._blender_operations = []
        self._imports = []
        self.import_module("bpy")
        self.import_module("bmesh")
        self.import_module("numpy",as_name="np")
        from blender_script_creator.geometry import get_or_create_object
        self.register_blender_function(get_or_create_object)

    def import_module(self, module_name, from_pack=None, as_name=None):
        self._imports.append(
            ("from {} ".format(from_pack) if from_pack else "") +
            ("import {} ".format(module_name)) +
            ("as {}".format(as_name) if as_name else "")
        )

    @staticmethod
    def main():
        print("hello world")

    def to_script(self):
        s=""
        for ip in self._imports:
           s+=ip+"\n"
        s+="\n"

        m=self.main
        if isinstance(m,(BlenderFunction,BlenderClass)):
            self.register_blender_dependencies(m)
            m=m.func

        for f  in self._blender_functions:
            if isinstance(f,BlenderClass):
                s+=f.to_code(f)+"\n"
            else:
                s+=f.to_code()+"\n"

        for v in self._blender_variables:
            s+=v.to_code()+"\n"

        s+="#OBJETCS\n"
        for obj in self._needed_objects:
            s+="{}=get_or_create_object('{}',{},{})\n".format(obj[0],obj[0],obj[1].__name__,",".join("{}={}".format(k,v) for k,v in obj[2].items()))

        m  = inspect.getsource(m)

        m = m.replace("\t","    ")
        #print(m)
        while not m.replace(" ","").startswith("def"):
            m = m.split("\n",maxsplit=1)[1]
        m = m.split("\n",maxsplit=1)[1]
        #print(m)
        indent=1000
        for line in m.split("\n"):
            i=0
            if len(line.replace(" ",""))>0:
                while line[0]==" " and i <= indent:
                    line=line[1:]
                    i+=1
                indent=min(indent,i)

        m_lines=[]
        for line in m.split("\n"):
            if len(line)>0:
                m_lines.append(line[indent:])
        m="\n".join(m_lines)

        s+=m+"\n"

        s+="print('DONE')"
        return s

    def __str__(self):
        return self.to_script()

    def register_blender_function(self, m:BlenderFunction):
        if m in self._blender_functions:
            return

        self.register_blender_dependencies(m)
        self._blender_functions.append(m)

    def register_blender_variable(self,var):
        self._blender_variables.append(var)

    def register_blender_class(self,cls:BlenderClass):
        if cls in self._blender_functions:
            return
        self.register_blender_dependencies(cls)
        for superclass in reversed(cls.mro()):
            if superclass!=cls:
                if issubclass(superclass,BlenderClass):
                    self.register_blender_class(superclass)

        self._blender_functions.append(cls)
#        print(cls,cls.mro())

    def register_blender_dependencies(self, m:(BlenderFunction,BlenderClass)):
        for d in m.dependencies:
            if type(d)==type(BlenderClass) and issubclass(d,BlenderClass):
                self.register_blender_class(d)
            elif isinstance(d,BlenderFunction):
                self.register_blender_function(d)
            elif isinstance(d,BlenderVariable):
                self.register_blender_variable(d)
            else:
                print(type(d))
                raise ValueError()

    def register_object(self,name,creator,**kwargs):
        self._needed_objects.append((name,creator,kwargs))