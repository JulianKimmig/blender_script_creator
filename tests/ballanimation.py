
from blender_script_creator.geometry import create_sphere, get_or_create_object, BlenderObject
from blender_script_creator.scene import delete_all_but, store_scene
from blender_script_creator.script import BlenderScript, blender_function
import numpy as np

script = BlenderScript()


@blender_function(dependencies=[create_sphere, get_or_create_object,delete_all_but,store_scene])
def ball_main():
    ##init
    NBALLS = 100
    CUBE=30
    MAX_SPEED=4

    all_balls = []

    for i in range(NBALLS):
        all_balls.append(get_or_create_object("ball{}".format(i), create_sphere))

    for ball in all_balls:
        ball.set_location(np.random.random()*CUBE,np.random.random()*CUBE,np.random.random()*CUBE)


    delete_all_but(all_balls)
    store_scene("ini")


    speed=np.random.random(3*NBALLS).reshape(3,-1)
    speed=MAX_SPEED*np.random.random(NBALLS)*(speed)
    speed=speed.T


script.main = ball_main



with open(__file__.replace(".py","_blend.py"), "w+") as f:
    f.write(script.to_script())
