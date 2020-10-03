import numpy as np
from blender_script_creator import bpy
from blender_script_creator.geometry import BlenderObject, create_plain_object
from blender_script_creator.materials import Material
from blender_script_creator.script import BlenderClass, blender_function


class BlenderAnimationTracker(BlenderClass):
    dependencies = [Material, BlenderObject]

    def __init__(self, fps=24):
        self._finish_hooks = []
        self._names_frames = {}
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

    def seconds_to_frames(self, s):
        return self._fps * s

    def frames_to_seconds(self, f):
        return f / self._fps

    def go_to_second(self, s):
        self.go_to_frame(self.seconds_to_frames(s))

    def run_seconds(self, s):
        self.run_frames(self.seconds_to_frames(s))

    def finish_animation(self,start=None,end=None):
        if start is None:
            start = 0
        if isinstance(start,str):
            start = self.get_frame(start)
        if end is None:
            end = self._max_frame
        if isinstance(end,str):
            end = self.get_frame(end)
        bpy.context.scene.frame_start = start
        bpy.context.scene.frame_end = end

        for fh in self._finish_hooks:
            fh(self)

    def clear_all(self):
        for a in bpy.data.actions:
            bpy.data.actions.remove(a)

    def performe_keyframe_op(self, obj, data_path, frames=0, reverse=False, interpolation=None):
        kf = obj.keyframe_insert(data_path=data_path, frame=self.current_frame)

        if interpolation is not None:
            action = obj.animation_data.action
            # kf.interpolation ="LINEAR"
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
            if interpolation is not None:
                action = obj.animation_data.action
                # kf.interpolation ="LINEAR"
                fcurves = [fc for fc in action.fcurves if fc.data_path == data_path]
                for fc in fcurves:
                    for kfp in fc.keyframe_points:
                        if kfp.co.x == self.current_frame:
                            kfp.interpolation = interpolation
            if reverse:
                self.go_to_frame(f)

        return compl

    def move_object(self, obj, x=0, y=0, z=0, delta=False, time=0, reverse=False, interpolation=None):
        if isinstance(obj, BlenderObject):
            obj = obj.obj
        kfcb = self.performe_keyframe_op(obj, "location", frames=self.seconds_to_frames(time), reverse=reverse,
                                         interpolation=interpolation)

        vec = np.array([x, y, z], dtype=float)
        curr_loc = np.array(obj.location, dtype=float)
        if delta:
            obj.location = curr_loc + vec
            delta = vec
        else:
            obj.location = vec
            delta = np.array(obj.location) - curr_loc

        kfcb()

        return delta

    def scale_object(self, obj, x=0, y=0, z=0, delta=False, time=0, reverse=False, interpolation=None):
        if isinstance(obj, BlenderObject):
            obj = obj.obj
        kfcb = self.performe_keyframe_op(obj, "scale", frames=self.seconds_to_frames(time), reverse=reverse,
                                         interpolation=interpolation)

        vec = np.array([x, y, z], dtype=float)
        curr_scale = np.array(obj.scale, dtype=float)
        if delta:
            obj.location = curr_scale * vec
            delta = vec
        else:
            obj.scale = vec
            delta = np.array(obj.scale) / curr_scale

        kfcb()

        return delta

    def move_objects(self, objs, x=0, y=0, z=0, delta=False, time=0, reverse=False, interpolation=None):
        delta =  self.move_object(objs[0],x=x,y=y,z=z,delta=delta,time=time,reverse=True,interpolation=interpolation)

        if len(objs)>1:
            for obj in objs[1:]:
                self.move_object(obj,*delta,delta=True,time=time,reverse=True,interpolation=interpolation)

        if not reverse:
            self.run_seconds(time)
        return delta


    def rotate_object(self, obj, x=0, y=0, z=0, delta=False, animator=None, time=0, reverse=False, interpolation=None):
        if isinstance(obj, BlenderObject):
            obj = obj.obj
        kfcb = self.performe_keyframe_op(obj, "rotation_euler", frames=self.seconds_to_frames(time), reverse=reverse,
                                         interpolation=interpolation)
        vec = np.array([x, y, z], dtype=float) * 2 * np.pi / 360
        curr_rot = np.array(obj.rotation_euler, dtype=float)
        if delta:
            obj.rotation_euler = curr_rot + vec
            delta = vec
        else:
            obj.rotation_euler = vec
            delta = np.array(obj.rotation_euler) - curr_rot

        kfcb()

        return delta * 360 / (2 * np.pi)

    def get_animation_data(self, obj):
        if isinstance(obj, Material):
            return obj.mat.node_tree.animation_data
        elif isinstance(obj, BlenderObject):
            return obj.obj.animation_data
        else:
            return obj.animation_data

    def delete_all_after_frame(self, obj, frame):
        anim = self.get_animation_data(obj)
        if anim is None:
            return
        action = anim.action
        if action is None:
            return
        fcurves = [fc for fc in action.fcurves]
        for fc in fcurves:
            for kfp in list(fc.keyframe_points):
                if kfp.co.x > frame:
                    #                    action.fcurves.remove(fc)
                    #                   break
                    fc.keyframe_points.remove(kfp)

    def change_node_value(self, socket, value, time=0, reverse=False, interpolation=None):
        node = socket.node
        cb = self.performe_keyframe_op(socket.socket, "default_value", frames=self.seconds_to_frames(time),
                                       reverse=reverse, interpolation=None)
        if interpolation is not None:
            fc = node.tree.animation_data.action.fcurves.find('nodes["{}"].inputs[{}].default_value'.format(node.name,socket.number))
            for kfp in fc.keyframe_points:
                if kfp.co.x == self.current_frame:
                    kfp.interpolation = interpolation

        socket.value = value
        cb()
        if interpolation is not None:
            fc = node.tree.animation_data.action.fcurves.find('nodes["{}"].inputs[{}].default_value'.format(node.name,socket.number))
            for kfp in fc.keyframe_points:
                if kfp.co.x == self.current_frame:
                    kfp.interpolation = interpolation

        # s="nodes['{}'].inputs[{}].default_value".format(node.name,socket.number)
        # print(s)
        # self.performe_keyframe_op(obj.node_tree,s,frames=self.seconds_to_frames(time),reverse=reverse,interpolation=interpolation)

    def save_frame(self, name):
        self._names_frames[name]=self.current_frame

    def get_frame(self, name):
        return self._names_frames[name]

    def register_finish_hook(self, callable):
        self._finish_hooks.append(callable)


class Camera(BlenderObject):
    def __init__(self, obj, name, location=(0, 0, 12), rotation_euler=(0, 0, 0), lens=18):
        super().__init__(obj, name)
        self.location = location
        self.set_rotation(*rotation_euler)
        self.lens = lens
        if bpy.context.scene.camera is None:
            self.set_active_cam()

    def set_active_cam(self):
        bpy.context.scene.camera = self.obj

    @property
    def lens(self):
        return self.obj.data.lens

    @lens.setter
    def lens(self, lens):
        self.obj.data.lens = lens

    @classmethod
    def new(cls, name, **kwargs):
        print("NEW CAMERA",name)
        cam_data = bpy.data.cameras.new(name)
        cam = Camera(create_plain_object(name, cam_data), name, **kwargs)
        return cam