#!/usr/bin/env python3
import rospy
from mavros_msgs.srv import StreamRate


def main():
    rospy.init_node("ensure_mavros_stream_rate")
    service_name = rospy.get_param("~service", "/mavros/set_stream_rate")
    stream_id = int(rospy.get_param("~stream_id", 0))
    stream_rate = int(rospy.get_param("~stream_rate", 50))
    check_topics = [
        topic.strip()
        for topic in rospy.get_param(
            "~check_topics", "/mavros/imu/data,/mavros/local_position/pose"
        ).split(",")
        if topic.strip()
    ]
    timeout = float(rospy.get_param("~timeout", 90.0))

    deadline = rospy.Time.now() + rospy.Duration(timeout)
    rospy.loginfo("Waiting for %s", service_name)
    rospy.wait_for_service(service_name)
    set_stream_rate = rospy.ServiceProxy(service_name, StreamRate)

    while not rospy.is_shutdown() and rospy.Time.now() < deadline:
        try:
            set_stream_rate(stream_id, stream_rate, True)
        except rospy.ServiceException as exc:
            rospy.logwarn("Failed to request MAVROS stream rate: %s", exc)
            rospy.sleep(1.0)
            continue

        missing = []
        for topic in check_topics:
            try:
                rospy.wait_for_message(topic, rospy.AnyMsg, timeout=2.0)
            except rospy.ROSException:
                missing.append(topic)

        if not missing:
            rospy.loginfo(
                "MAVROS streams active at %s Hz for: %s",
                stream_rate,
                ", ".join(check_topics),
            )
            return

        rospy.loginfo("Waiting for MAVROS stream topics: %s", ", ".join(missing))
        rospy.sleep(1.0)

    rospy.logerr("Timed out waiting for MAVROS streams: %s", ", ".join(check_topics))


if __name__ == "__main__":
    main()
