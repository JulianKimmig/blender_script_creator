from blender_script_creator import bpy
from blender_script_creator.animation import BlenderAnimationTracker
from blender_script_creator.geometry import create_sphere, get_or_create_object
from blender_script_creator.materials import new_material, get_or_create_material
from blender_script_creator.scene import delete_all_but, store_scene
from blender_script_creator.script import BlenderScript, blender_function

import numpy as np

script = BlenderScript()





@blender_function(dependencies=[create_sphere, get_or_create_object,delete_all_but,store_scene,BlenderAnimationTracker,get_or_create_material])
def ball_main():
    ##init
    NBALLS = 10
    CUBE=30
    MAX_SPEED=100
    FPS=24
    TIME=1

    anim = BlenderAnimationTracker(fps=FPS)
    all_balls = []
    base_mat= get_or_create_material(name="ball_base_mat")
    for i in range(NBALLS):
        ball = get_or_create_object("ball{}".format(i), create_sphere)
        ball.material = base_mat
        all_balls.append(ball)

    for ball in all_balls:
        ball.obj.animation_data_clear()
        ball.location = np.random.random(3)*CUBE

    delete_all_but(all_balls)
    store_scene("ini")


    speed=(np.random.random(3*NBALLS)-0.5).reshape(3,-1)
    speed = speed/np.linalg.norm(speed,axis=0)
    speed=(MAX_SPEED*np.random.random(NBALLS))*(speed)
    speed = speed.T

    pos=[ball.location for ball in all_balls]
    for i,ball in enumerate(all_balls):
        anim.move_object(ball,*pos[i],interpolation="LINEAR")

    def is_out(xyz):
        for c in xyz:
            if c < 0 or c > CUBE:
                return True
        return False

    def reenter(xyz,speeds):
        for i,c in enumerate(xyz):
            if c < 0:
                xyz[i]=-c
                speeds[i]=-speeds[i]
            if c > CUBE:
                xyz[i]=2*CUBE-c
                speeds[i]=-speeds[i]
        return xyz,speeds

    for f in range(TIME*FPS):
        next_locs = pos + speed/FPS
        for i in range(len(next_locs)):
            while is_out(next_locs[i]):
                anim.move_object(all_balls[i],*pos[i],interpolation="LINEAR")
                next_locs[i], speed[i] = reenter(next_locs[i], speed[i])

        pos = next_locs
        anim.run_frames(1)

    for i,ball in enumerate(all_balls):
        anim.move_object(ball,*pos[i],interpolation="LINEAR")


    anim.finish_animation()

script.main = ball_main



with open(__file__.replace(".py","_blend.py"), "w+") as f:
    f.write(script.to_script())

import os

d='''
import sys
sys.path.append('{}')
import importlib
import {} as blenderscript
import importlib
importlib.reload(blenderscript)
'''.format(
    os.path.dirname(__file__.replace(".py","_blend.py")),
    os.path.basename(__file__.replace(".py","_blend.py")).replace(".py","")
           )

print(d)


print()