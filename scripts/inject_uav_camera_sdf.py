#!/usr/bin/env python3
"""Create a PX4 SDF copy with a forward RGB camera on base_link."""

import argparse
import pathlib
import xml.etree.ElementTree as ET


def add_text(parent, tag, text):
    child = ET.SubElement(parent, tag)
    child.text = str(text)
    return child


def build_camera_sensor(args):
    sensor = ET.Element("sensor", {"type": "camera", "name": "front_rgb_camera"})
    add_text(sensor, "pose", args.camera_pose)
    add_text(sensor, "always_on", "1")
    add_text(sensor, "update_rate", str(args.update_rate))
    add_text(sensor, "visualize", "0")

    camera = ET.SubElement(sensor, "camera", {"name": "front_rgb_camera"})
    add_text(camera, "horizontal_fov", str(args.horizontal_fov))
    image = ET.SubElement(camera, "image")
    add_text(image, "width", str(args.width))
    add_text(image, "height", str(args.height))
    add_text(image, "format", "R8G8B8")
    clip = ET.SubElement(camera, "clip")
    add_text(clip, "near", "0.05")
    add_text(clip, "far", "50.0")

    plugin = ET.SubElement(
        sensor,
        "plugin",
        {"name": "front_rgb_camera_controller", "filename": "libgazebo_ros_camera.so"},
    )
    namespace = args.robot_namespace.strip("/")
    add_text(plugin, "robotNamespace", f"/{namespace}" if namespace else "")
    add_text(plugin, "cameraName", args.camera_name)
    add_text(plugin, "imageTopicName", "image_raw")
    add_text(plugin, "cameraInfoTopicName", "camera_info")
    frame_name = f"{namespace}/front_rgb_camera_optical_frame" if namespace else "front_rgb_camera_optical_frame"
    add_text(plugin, "frameName", frame_name)
    return sensor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Input PX4 SDF path")
    parser.add_argument("--output", required=True, help="Output SDF path")
    parser.add_argument("--robot-namespace", default="none_iris")
    parser.add_argument("--camera-name", default="front_camera")
    parser.add_argument("--camera-pose", default="0.20 0 0.08 0 0 0")
    parser.add_argument("--update-rate", type=float, default=15.0)
    parser.add_argument("--horizontal-fov", type=float, default=1.0471975512)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    args = parser.parse_args()

    source = pathlib.Path(args.source)
    output = pathlib.Path(args.output)
    if not source.is_file():
        raise FileNotFoundError(source)

    tree = ET.parse(str(source))
    root = tree.getroot()
    base_link = root.find(".//model/link[@name='base_link']")
    if base_link is None:
        raise RuntimeError(f"No base_link found in {source}")

    for old_sensor in list(base_link.findall("sensor")):
        if old_sensor.get("name") == "front_rgb_camera":
            base_link.remove(old_sensor)
    base_link.append(build_camera_sensor(args))

    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass

    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(output), encoding="utf-8", xml_declaration=False)


if __name__ == "__main__":
    main()
