from blender_script_creator import bpy
from blender_script_creator.animation import BlenderAnimationTracker
from blender_script_creator.geometry import create_sphere, get_or_create_object
from blender_script_creator.materials import new_material, get_or_create_material, MixShader
from blender_script_creator.scene import delete_all_but, store_scene
from blender_script_creator.script import BlenderScript, blender_function

import numpy as np

script = BlenderScript()





@blender_function(dependencies=[create_sphere, get_or_create_object,delete_all_but,store_scene,BlenderAnimationTracker,get_or_create_material])
def ball_main():
    ##init
    NBALLS = 10
    CUBE=30
    MAX_SPEED=10
    FPS=24
    TIME=50
    SEED=100
    BLINK_TIME=1
    np.random.seed(SEED)

    anim = BlenderAnimationTracker(fps=FPS)
    anim.clear_all()
    all_balls = []

    base_mat= get_or_create_material(name="ball_base_mat",)
    mout=base_mat.get_node("Material Output")

    mixer = base_mat.get_or_create_node(name="mixer1",type="ShaderNodeMixShader")
    base_mat.connect_node_sockets(mixer.Shader_2, mout.Surface)
    mixer.Fac.value = 1

    em = base_mat.get_or_create_node(name="emission",type="ShaderNodeEmission")
    base_mat.connect_node_sockets(em.Emission, mixer.Shader_0)

    glass = base_mat.get_or_create_node(name="glass",type="ShaderNodeBsdfGlass")
    base_mat.connect_node_sockets(glass.BSDF, mixer.Shader_1)

    rgb = base_mat.get_or_create_node(name="rgb",type="ShaderNodeRGB")
    rgb.Color.value=(0,0.7,1,1)
    base_mat.connect_node_sockets(rgb.Color, glass.Color)
    for i in range(NBALLS):
        ball = get_or_create_object("ball{}".format(i), create_sphere)
        ball.material = base_mat.get_or_copy("ball{}_mat".format(i))
        all_balls.append(ball)

    delete_all_but(all_balls)

    for ball in all_balls:
        anim.delete_all_after_frame(ball,0)
        #ball.obj.animation_data_clear()
        ball.location = np.random.random(3)*CUBE
        #anim.go_to_frame(1)

    speed=(np.random.random(3*NBALLS)-0.5).reshape(3,-1)
    speed = speed/np.linalg.norm(speed,axis=0)
    speed=(MAX_SPEED*np.random.random(NBALLS))*(speed)
    speed = speed.T

    pos=[ball.location for ball in all_balls]
    for i,ball in enumerate(all_balls):
        anim.go_to_frame(0)
        anim.move_object(ball,*pos[i],interpolation="LINEAR")
        anim.change_node_value(ball.material.get_node("mixer1").Fac,1.0,time=0)

    anim.go_to_frame(0)


    store_scene("ini")
    print("POST INI")



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

    last_p=[None for ball in all_balls]

    for f in range(TIME*FPS):
        next_locs = pos + speed/FPS
        #wo=False
        for i in range(len(next_locs)):

            while is_out(next_locs[i]):
                anim.move_object(all_balls[i],*pos[i],interpolation="LINEAR")
                next_locs[i], speed[i] = reenter(next_locs[i], speed[i])
                cf=anim.current_frame
                if last_p[i] is not None:
                    d=anim.frames_to_seconds(f-last_p[i])
                    if d < BLINK_TIME:
                        anim.go_to_frame(cf-1)
                        anim.change_node_value(all_balls[i].material.get_node("mixer1").Fac,
                                               1-(0.5*d/BLINK_TIME),
                                               time=0.00)
                        anim.go_to_frame(cf)
                anim.change_node_value(all_balls[i].material.get_node("mixer1").Fac,0.5,time=0.001,)
                anim.delete_all_after_frame(all_balls[i].material,anim.current_frame)
                anim.change_node_value(all_balls[i].material.get_node("mixer1").Fac,1,time=BLINK_TIME,)
                anim.go_to_frame(cf)
                last_p[i]=cf
                wo=True
        #if wo:
        #    break
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