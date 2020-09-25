import numpy as np
from blender_script_creator import bpy
from blender_script_creator.geometry import BlenderObject
from blender_script_creator.script import BlenderClass


class BlenderAnimationTracker(BlenderClass):
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

    def go_to_second(self, s):
        self.go_to_frame(self.seconds_to_frames(s))

    def run_seconds(self, s):
        self.run_frames(self.seconds_to_frames(s))

    def finish_animation(self):
        bpy.context.scene.frame_end = self._max_frame

    def performe_keyframe_op(self,obj,data_path,frames,reverse=False,interpolation=None):
        kf = obj.keyframe_insert(data_path=data_path, frame=self.current_frame)
        action = obj.animation_data.action

        if interpolation is not None:

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

