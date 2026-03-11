import os
import sys
if os.geteuid() != 0:
    os.execvp("sudo", ["sudo"] + ["python"] + sys.argv)
from ctypes import *
import numpy as np
import cv2

class FrontCamera():
    def __init__(self, networkInterface="eth0"):
        self.lib = cdll.LoadLibrary("/home/unitree/workspace/camera/front_camera/build/libfront_camera.so")
        self.lib.init_camera.argtypes = [c_char_p]
        self.lib.init_camera.restype = c_void_p
        self.client = self.lib.init_camera(networkInterface.encode('utf-8'))
        self.img_buffer = np.zeros(dtype=np.uint8, shape=(400000,1))

    def capture(self):
        res = self.lib.capture_img(c_void_p(self.client), self.img_buffer.ctypes.data_as(POINTER(c_ubyte)))
        if res == -1:
            return None
        else:
            img = cv2.imdecode(self.img_buffer[:res], cv2.IMREAD_COLOR)
            return img
        
if __name__ == "__main__":
    cam = FrontCamera()
    while True:
        img = cam.capture()
        if img is not None:
            cv2.imshow("front_camera", img)
        if cv2.waitKey(1) == ord('q'):
            break