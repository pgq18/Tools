#!/usr/bin/env python
import math
import requests
import rospy
import tf
from tf.transformations import quaternion_matrix, euler_from_quaternion


SERVER_URL = "http://192.168.3.17:5000"  # Change to your Flask server IP
ROBOT_ID   = "dog2"                     # Robot ID
MAP_FRAME  = "map"                      # Map frame from slam_toolbox
BASE_FRAME = "base_link"                # Robot base frame


class TfPoseSender:
    def __init__(self):
        # Initialize node
        rospy.init_node("dog_tf_sender")

        # TF Listener
        self.tf_listener = tf.TransformListener()

        # Timer, query TF and send at 10Hz
        rospy.Timer(rospy.Duration(0.1), self.timer_cb)

    def timer_cb(self, event):
        try:
            # Get TF: map -> base_link
            (trans, rot) = self.tf_listener.lookupTransform(
                MAP_FRAME,
                BASE_FRAME,
                rospy.Time(0)  # Latest available time
            )
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException) as e:
            rospy.logwarn("Could not get transform {}->{}: {}".format(MAP_FRAME, BASE_FRAME, e))
            return

        x = trans[0]
        y = trans[1]
        
        # Calculate yaw from quaternion (rotation around z-axis)
        _, _, yaw = euler_from_quaternion(rot)

        data = {
            "id": ROBOT_ID,
            "x": x,
            "y": y,
            "angle": yaw
        }
        print(data)
        try:
            # Send position data via HTTP POST request
            response = requests.post(
                SERVER_URL + "/update_robot_position",
                json=data,
                timeout=1.0
            )
            if response.status_code != 200:
                rospy.logwarn("Failed to send position data. Status code: {}".format(response.status_code))
        except Exception as e:
            rospy.logwarn("POST request failed: {}".format(e))


def main():
    tf_pose_sender = TfPoseSender()
    try:
        rospy.spin()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()