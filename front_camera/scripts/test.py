import os
import sys
if os.geteuid() != 0:
    os.execvp("sudo", ["sudo"] + ["python"] + sys.argv)
from ctypes import *
import time
import numpy as np
import cv2

lib = cdll.LoadLibrary("/home/unitree/workspace/camera/front_camera/build/libfront_camera.so")

lib.test_str.argtypes = [c_char_p]
lib.test_str.restype = c_char_p
res = lib.test_str(b"Hello, ctypes!")
print(res.decode())

cam_pic = np.zeros(dtype=np.uint8, shape=(5,))
res = lib.test_vector(cam_pic.ctypes.data_as(POINTER(c_ubyte)))
print(res)
print(cam_pic)


lib.init_camera.argtypes = [c_char_p]
lib.init_camera.restype = c_void_p
client = lib.init_camera(b"eth0")

cam_pic = np.zeros(dtype=np.uint8, shape=(300000,1))
res = lib.capture_img(c_void_p(client), cam_pic.ctypes.data_as(POINTER(c_ubyte)))
print(res)
# print(cam_pic)
img = cv2.imdecode(cam_pic, cv2.IMREAD_COLOR)
cv2.imwrite("test.jpg", img)

res = lib.add(1, 9)
print(res)
