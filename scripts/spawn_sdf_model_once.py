#!/usr/bin/env python3

import sys
import time

import rospy
from gazebo_msgs.srv import GetWorldProperties, SpawnModel
from geometry_msgs.msg import Pose


def model_exists(get_world, model_name):
    try:
        return model_name in get_world().model_names
    except rospy.ServiceException:
        return False


def main():
    rospy.init_node("spawn_sdf_model_once")
    model_file = rospy.get_param("~model_file")
    model_name = rospy.get_param("~model_name")
    reference_frame = rospy.get_param("~reference_frame", "world")
    verify_timeout = float(rospy.get_param("~verify_timeout", 5.0))

    pose = Pose()
    pose.position.x = float(rospy.get_param("~x", 0.0))
    pose.position.y = float(rospy.get_param("~y", 0.0))
    pose.position.z = float(rospy.get_param("~z", 0.0))
    pose.orientation.w = 1.0

    with open(model_file, "r", encoding="utf-8") as model_stream:
        model_xml = model_stream.read()

    rospy.wait_for_service("/gazebo/get_world_properties")
    rospy.wait_for_service("/gazebo/spawn_sdf_model")
    get_world = rospy.ServiceProxy(
        "/gazebo/get_world_properties", GetWorldProperties
    )
    spawn = rospy.ServiceProxy("/gazebo/spawn_sdf_model", SpawnModel)

    if model_exists(get_world, model_name):
        rospy.loginfo("Gazebo model %s already exists.", model_name)
        return 0

    try:
        response = spawn(model_name, model_xml, "", pose, reference_frame)
        if response.success:
            rospy.loginfo("Spawned Gazebo model %s.", model_name)
            return 0
        rospy.logwarn("Gazebo spawn response: %s", response.status_message)
    except rospy.ServiceException as error:
        rospy.logwarn("Gazebo spawn service returned an error: %s", error)

    deadline = time.monotonic() + verify_timeout
    while time.monotonic() < deadline and not rospy.is_shutdown():
        if model_exists(get_world, model_name):
            rospy.loginfo(
                "Gazebo model %s exists despite the spawn timeout.", model_name
            )
            return 0
        time.sleep(0.1)

    rospy.logerr("Gazebo model %s was not created.", model_name)
    return 1


if __name__ == "__main__":
    sys.exit(main())
