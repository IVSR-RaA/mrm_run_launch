cmake_minimum_required(VERSION 3.0.2)
project(mrm_run_launch)

find_package(catkin REQUIRED)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/ensure_mavros_stream_rate.py
  scripts/inject_uav_camera_sdf.py
  scripts/spawn_sdf_model_once.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config models urdf
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
