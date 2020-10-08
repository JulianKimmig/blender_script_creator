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
        if isinstance(f,str):
            f = self.get_frame(f)
        self._max_frame = max(self._max_frame, f)
        self.current_frame = f

    def run_frames(self, f):
        self.go_to_frame(self.current_frame + np.ceil(f))

    def seconds_to_frames(self, s):
        if s is None:
            return None
        return self._fps * s

    def frames_to_seconds(self, f):
        if f is None:
            return None
        return f / self._fps

    def go_to_second(self, s):
        self.go_to_frame(self.seconds_to_frames(s))

    def run_seconds(self, s):
        self.run_frames(self.seconds_to_frames(s))

    def finish_animation(self,start=None,end=None,current=None):
        if start is None:
            start = 0
        if isinstance(start,str):
            start = self.get_frame(start)
        if end is None:
            end = self._max_frame
        if isinstance(end,str):
            end = self.get_frame(end)

        if current is None:
            current = start
        if isinstance(current,str):
            current = self.get_frame(current)

        bpy.context.scene.frame_start = start
        bpy.context.scene.frame_end = end
        bpy.context.scene.frame_current = current

        for fh in self._finish_hooks:
            fh(self)

        bpy.ops.screen.animation_play()

    def clear_all(self):
        for a in bpy.data.actions:
            bpy.data.actions.remove(a)


    def insert_keyframe(self,obj,data_path):
        return obj.keyframe_insert(data_path=data_path, frame=self.current_frame)

    def performe_keyframe_op(self, obj, data_path, frames=0, reverse=False, interpolation=None):
        if frames is None:
            frames = 1
        kf = self.insert_keyframe(obj,data_path=data_path)

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
        if time is None:
            time = self.frames_to_seconds(1)
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

    def bevel_start_end(self, obj,start=0,end=1, time=0, reverse=False, interpolation=None):
        if time is None:
            time = self.frames_to_seconds(1)
        if isinstance(obj, BlenderObject):
            obj = obj.obj

        kfcb1 = self.performe_keyframe_op(obj.data, "bevel_factor_end", frames=self.seconds_to_frames(time), reverse=reverse,
                                         interpolation=interpolation)
        kfcb2 = self.performe_keyframe_op(obj.data, "bevel_factor_start", frames=self.seconds_to_frames(time), reverse=reverse,
                                         interpolation=interpolation)

        obj.data.bevel_factor_end = end
        obj.data.bevel_factor_start = start

        kfcb1()
        kfcb2()


    def scale_object(self, obj, x=0, y=0, z=0, delta=False, time=0, reverse=False, interpolation=None):
        if time is None:
            time = self.frames_to_seconds(1)
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
        if time is None:
            time = self.frames_to_seconds(1)
        delta =  self.move_object(objs[0],x=x,y=y,z=z,delta=delta,time=time,reverse=True,interpolation=interpolation)

        if len(objs)>1:
            for obj in objs[1:]:
                self.move_object(obj,*delta,delta=True,time=time,reverse=True,interpolation=interpolation)

        if not reverse:
            self.run_seconds(time)
        return delta


    def rotate_object(self, obj, x=0, y=0, z=0, delta=False, animator=None, time=0, reverse=False, interpolation=None):
        if time is None:
            time = self.frames_to_seconds(1)
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
        self._tracker={}
        for name, tr in self.obj.constraints.items():
            if tr.type == "TRACK_TO":
                if tr.target in self._tracker:
                     self.obj.constraints.remove(tr)
                else:
                    self._tracker[tr.target]=tr

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

    def stop_tracking(self,animator=None,frames=None):
        for ob,tr in self._tracker.items():
            if tr.influence != 0:
                if animator:
                    cb = animator.performe_keyframe_op(tr,"influence",frames=frames,reverse=True)
                tr.influence = 0
                if animator:
                    cb()


    def track(self,obj,influence=1,stop_other=True,animator=None,frames=None):
        if isinstance(obj,BlenderObject):
            obj=obj.obj


        if obj not in self._tracker:
            obj_tracker = self.obj.constraints.new(type='TRACK_TO')
            self._tracker[obj] = obj_tracker
            obj_tracker.target = obj
            self._tracker[obj].influence = 0
            if animator:
                cf=animator.current_frame
                animator.go_to_frame(0)
                cb = animator.performe_keyframe_op(self._tracker[obj],"influence",frames=None,reverse=True)
                animator.go_to_frame(cf)


        if stop_other:
            own=self._tracker[obj].influence
            self.stop_tracking(animator=animator,frames=frames)
            self._tracker[obj].influence = own

        if animator:
            cb = animator.performe_keyframe_op(self._tracker[obj],"influence",frames=frames,reverse=True)
        self._tracker[obj].influence = influence
        if animator:
            cb()