# mrm_run_launch

Launch-only package for manually starting the multi-robot mapping runtime.

This package follows the same isolation model as `/home/nlg/all_ws/run`: UGV,
UAV, Husky, and base station use different ROS masters. UAV, UGV, and Husky also
use different Gazebo masters so robot-local topics do not collide.

## Launch Files

```text
base_runtime.launch      base station, central LAMP, received VAE decoders
ugv_gazebo.launch        UGV Gazebo world on the UGV ROS/Gazebo master
ugv_runtime.launch       UGV/MOCHA, Super-LIO, VAE, local LAMP input, optional distributed LAMP
ugv_cmu_planner.launch   CMU local planner for UGV, using /lio/odom and /lio/cloud_world
husky_runtime.launch     Husky/MOCHA, Super-LIO, VAE, local LAMP input, optional distributed LAMP/planner
uav_runtime.launch       UAV PX4/Gazebo/MAVROS/MOCHA, Super-LIO, VAE, local LAMP input, optional distributed LAMP
uav_sequence_controller.launch PX4 geometric controller plus sequence_controller parser
uav_ego_planner.launch   EGO-Planner, raw VLP-16 cloud adapter, and optional Gazebo test wall
uav_sim_mocha.launch     UAV PX4/MAVROS/MOCHA helper used by uav_runtime.launch
visual_tools.launch      RViz, rqt_graph, rqt_tf_tree, rqt_console, gzclient
```

## Optional RGB Cameras

Jackal and Husky use URDF extras. Enable them directly:

```bash
roslaunch mrm_run_launch ugv_runtime.launch enable_camera:=true
roslaunch mrm_run_launch husky_runtime.launch enable_camera:=true
```

UAV/PX4 uses SDF, so generate a camera-enabled SDF first:

```bash
rosrun mrm_run_launch inject_uav_camera_sdf.py \
  --source /home/nlg/PX4-Autopilot/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/tarot/tarot.sdf \
  --output /tmp/none_iris_rgb_camera.sdf \
  --robot-namespace none_iris

roslaunch mrm_run_launch uav_runtime.launch \
  enable_camera:=true \
  uav_sdf:=/tmp/none_iris_rgb_camera.sdf
```

Expected image topics:

```text
/jackal/front_camera/image_raw
/none_iris/front_camera/image_raw
/husky/front_camera/image_raw
```

## Isolation Rule

Do not run UGV, UAV, and Husky on the same `ROS_MASTER_URI` with the current
launch files. Several nodes still use global topic and node names:

```text
/lio/odom
/lio/cloud_body
/keyframe_vae
/integrate_database
/translator
/topic_publisher
```

If multiple robots use the same ROS master, these topics and nodes can collide or
mix data. MOCHA may then store a mixed `/keyframe_vae` stream under the wrong
robot.

Also do not point UGV, UAV, and Husky to the same `GAZEBO_MASTER_URI`. A shared
Gazebo world requires one ROS master for `/gazebo/*` services, which brings back
the topic collision problem above unless the robot stacks are fully namespaced.

Use separate masters:

```text
UAV ROS master:     http://10.249.171.1:11313
UAV Gazebo master:  http://127.0.0.1:11345

UGV ROS master:     http://10.229.222.1:11312
UGV Gazebo master:  http://127.0.0.1:11346

Husky ROS master:   http://10.229.223.1:11314
Husky Gazebo master: http://127.0.0.1:11347

Base ROS master:    http://10.229.221.1:11311
```

## Virtual IP Setup

`run/run_mrm.sh` can add missing loopback aliases automatically, but it needs
valid sudo credentials first. Before starting the script, run:

```bash
sudo -v
```

Then start normally:

```bash
cd /home/nlg/all_ws
./run/run_mrm.sh --no-attach
```

To add the virtual IPs manually:

```bash
sudo ip addr add 10.249.171.1/24 dev lo
sudo ip addr add 10.229.222.1/24 dev lo
sudo ip addr add 10.229.223.1/24 dev lo
sudo ip addr add 10.229.221.1/24 dev lo
```

If an address already exists, `ip` may print `RTNETLINK answers: File exists`.
That is not a runtime problem.

Verify:

```bash
ip -o addr show dev lo | grep '10.249.171.1'
ip -o addr show dev lo | grep '10.229.222.1'
ip -o addr show dev lo | grep '10.229.223.1'
ip -o addr show dev lo | grep '10.229.221.1'
```

When the robots run on different physical machines, `127.0.0.1` means the local
machine. That is OK if each robot runs its own Gazebo locally. If you view a
remote Gazebo from another machine, set `GAZEBO_MASTER_URI` to that robot host's
reachable IP and port.

## Environment

UAV:

```bash
source /home/nlg/all_ws/devel/setup.bash
source /usr/share/gazebo/setup.bash
source $HOME/PX4-Autopilot/Tools/simulation/gazebo-classic/setup_gazebo.bash \
  $HOME/PX4-Autopilot \
  $HOME/PX4-Autopilot/build/px4_sitl_default
export ROS_PACKAGE_PATH=$HOME/PX4-Autopilot:$ROS_PACKAGE_PATH
export ROS_PACKAGE_PATH=$HOME/PX4-Autopilot/Tools/simulation/gazebo-classic/sitl_gazebo-classic:$ROS_PACKAGE_PATH
export ROS_MASTER_URI=http://10.249.171.1:11313
export ROS_IP=10.249.171.1
export GAZEBO_MASTER_URI=http://127.0.0.1:11345
```

UGV:

```bash
source /home/nlg/all_ws/devel/setup.bash
export ROS_MASTER_URI=http://10.229.222.1:11312
export ROS_IP=10.229.222.1
export GAZEBO_MASTER_URI=http://127.0.0.1:11346
```

Husky:

```bash
source /home/nlg/all_ws/devel/setup.bash
export ROS_MASTER_URI=http://10.229.223.1:11314
export ROS_IP=10.229.223.1
export GAZEBO_MASTER_URI=http://127.0.0.1:11347
```

Base:

```bash
source /home/nlg/all_ws/devel/setup.bash
export ROS_MASTER_URI=http://10.229.221.1:11311
export ROS_IP=10.229.221.1
```

## Commands

UGV centralized input mode:

```bash
# terminal 1
roscore -p 11312
```

```bash
# terminal 2
roslaunch mrm_run_launch ugv_gazebo.launch
```

```bash
# terminal 3
roslaunch mrm_run_launch ugv_runtime.launch \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_centralized.yaml \
  run_distributed_lamp:=false
```

`ugv_runtime.launch` starts the CMU planner by default. Disable it for a
mapping-only run:

```bash
roslaunch mrm_run_launch ugv_runtime.launch \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_centralized.yaml \
  run_cmu_planner:=false
```

The standalone planner launch is:

```bash
roslaunch mrm_run_launch ugv_cmu_planner.launch \
  state_estimation_topic:=/lio/odom \
  registered_scan_topic:=/lio/cloud_world \
  cmd_vel_topic:=/cmd_vel
```

UGV distributed mode:

```bash
# terminal 1
roscore -p 11312
```

```bash
# terminal 2
roslaunch mrm_run_launch ugv_gazebo.launch
```

```bash
# terminal 3
JACKAL_LASER_3D=1 roslaunch mrm_run_launch ugv_runtime.launch \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_distributed.yaml \
  run_distributed_lamp:=true
```

Husky centralized input mode:

```bash
# terminal 1
roscore -p 11314
```

```bash
# terminal 2
roslaunch mrm_run_launch husky_runtime.launch \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_centralized.yaml \
  run_distributed_lamp:=false \
  run_cmu_planner:=false
```

Husky distributed mode:

```bash
# terminal 1
roscore -p 11314
```

```bash
# terminal 2
roslaunch mrm_run_launch husky_runtime.launch \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_distributed.yaml \
  run_distributed_lamp:=true \
  run_cmu_planner:=false
```

UAV centralized input mode:

```bash
# terminal 1
roscore -p 11313
```

```bash
# terminal 2
roslaunch mrm_run_launch uav_runtime.launch \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_centralized.yaml \
  run_distributed_lamp:=false
```

`uav_runtime.launch` starts `uav_sequence_controller.launch` by default. Disable
it for mapping-only runs:

```bash
roslaunch mrm_run_launch uav_runtime.launch \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_centralized.yaml \
  run_distributed_lamp:=false \
  run_sequence_controller:=false
```

UAV sequence controller:

```bash
roslaunch mrm_run_launch uav_sequence_controller.launch \
  sequence_yaml:=$(rospack find sequence_controller)/cfg/run_mrm_uav_takeoff_land.yaml
```

The default sequence is a controller smoke test: take off to 2 m, then land.
It does not use GPS. Run the included local ENU square mission with:

```bash
roslaunch mrm_run_launch uav_sequence_controller.launch \
  sequence_yaml:=$(rospack find sequence_controller)/cfg/run_mrm_uav_local_square.yaml
```

The `move` points are absolute `[x, y, z]` coordinates in meters in the MAVROS
local ENU frame. The local server reads `/mavros/local_position/odom` and
publishes `quadrotor_msgs/PositionCommand` on `/controller/pos_cmd`.
The wrapper sets `mission_use_position_setpoints:=true`, so the geometric
controller forwards the generated positions to PX4 as local position
setpoints. Set that argument to `false` only when intentionally testing its
acceleration-feedback trajectory controller.

For a longer mission, add multiple `move` sections and finish with `land`.
`count` is the total number of sections, `goal` is the final section to
complete, and each section's one-based `failsafe` value should normally point
to the landing section. For example:

```yaml
count: 3
goal: 3
s1: {type: "takeoff", height: 2.0, timeout: 45.0, failsafe: 3}
s2:
  type: "move"
  count: 2
  timeout: 120.0
  failsafe: 3
  t1: [2.0, 0.0, 2.0]
  t2: [0.0, 0.0, 2.0]
s3: {type: "land", timeout: 60.0, failsafe: 3}
```

### EGO-Planner avoidance

`/home/nlg/ego-planner/devel` is the underlay for the EGO packages. Confirm the
overlay before launching:

```bash
cd /home/nlg/all_ws
catkin config --extend /home/nlg/ego-planner/devel
catkin build geometric_controller sequence_controller \
  super_lio_lamp_adapter mrm_run_launch --no-status -j2 -l2
```

Run the avoidance launch directly:

```bash
source /home/nlg/all_ws/devel/setup.bash
export ROS_MASTER_URI=http://10.249.171.1:11313
export ROS_IP=10.249.171.1

roslaunch mrm_run_launch uav_sequence_controller.launch \
  run_ego_planner:=true \
  mission_use_position_setpoints:=true \
  ego_spawn_test_obstacle:=true \
  sequence_yaml:=$(rospack find sequence_controller)/cfg/run_mrm_uav_ego_avoid.yaml
```

The UAV simulator and MAVROS must already be running. The launch transforms and
filters `/velodyne_points` into `/ego_planner/cloud_world`, uses
`/mavros/local_position/odom` for planning, and publishes EGO commands on
`/controller/pos_cmd`. Use `type: "avoid"` for mission stages that must pass
through EGO; `type: "move"` does not invoke obstacle avoidance.

`uav_sim_mocha.launch` runs `mavros_set_stream_rate`, which keeps requesting
MAVROS streams until `/mavros/imu/data` and `/mavros/local_position/pose` publish.
Use the original full sequence only when the GPS/marker/avoidance dependencies
are intended to run:

```bash
roslaunch mrm_run_launch uav_sequence_controller.launch \
  sequence_yaml:=$(rospack find sequence_controller)/cfg/seq.yaml \
  run_local_sequence_server:=false \
  run_gps_sequence_server:=true \
  run_external_scripts:=true
```

UAV distributed mode:

```bash
# terminal 1
roscore -p 11313
```

```bash
# terminal 2
roslaunch mrm_run_launch uav_runtime.launch \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_distributed.yaml \
  run_distributed_lamp:=true
```

Base centralized mode:

```bash
# terminal 1
roscore -p 11311
```

```bash
# terminal 2
roslaunch mrm_run_launch base_runtime.launch \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_centralized.yaml
```

Visual tools for one selected master:

```bash
# Base LAMP view
export ROS_MASTER_URI=http://10.229.221.1:11311
export ROS_IP=10.229.221.1
roslaunch mrm_run_launch visual_tools.launch run_gzclient:=false

# UAV Gazebo view
export ROS_MASTER_URI=http://10.249.171.1:11313
export ROS_IP=10.249.171.1
export GAZEBO_MASTER_URI=http://127.0.0.1:11345
roslaunch mrm_run_launch visual_tools.launch run_rviz:=false run_rqt_graph:=false run_tf_tree:=false run_rqt_console:=false

# UGV Gazebo view
export ROS_MASTER_URI=http://10.229.222.1:11312
export ROS_IP=10.229.222.1
export GAZEBO_MASTER_URI=http://127.0.0.1:11346
roslaunch mrm_run_launch visual_tools.launch run_rviz:=false run_rqt_graph:=false run_tf_tree:=false run_rqt_console:=false

# Husky Gazebo view
export ROS_MASTER_URI=http://10.229.223.1:11314
export ROS_IP=10.229.223.1
export GAZEBO_MASTER_URI=http://127.0.0.1:11347
roslaunch mrm_run_launch visual_tools.launch run_rviz:=false run_rqt_graph:=false run_tf_tree:=false run_rqt_console:=false
```

`run/run_mrm.sh` does not auto-start GUI debug tools. It starts runtime panes
plus six manual shells per running role. Start RViz, rqt, or `gzclient`
manually from those shells or from normal terminals.

UAV debug tools use:

```bash
ROS_MASTER_URI=http://10.249.171.1:11313
ROS_IP=10.249.171.1
GAZEBO_MASTER_URI=http://127.0.0.1:11345
```

UGV debug tools use:

```bash
ROS_MASTER_URI=http://10.229.222.1:11312
ROS_IP=10.229.222.1
GAZEBO_MASTER_URI=http://127.0.0.1:11346
```

Husky debug tools use:

```bash
ROS_MASTER_URI=http://10.229.223.1:11314
ROS_IP=10.229.223.1
GAZEBO_MASTER_URI=http://127.0.0.1:11347
```

For copy-paste RViz, rqt, Gazebo, and topic-check commands, see
`/home/nlg/all_ws/run/README.md`.

## Notes

All three launch-only robot runtimes default to the VLP-16/ground pcl-vae model:

```text
uav_runtime.launch: vae_robot_type:=ground
ugv_runtime.launch: vae_robot_type:=ground
husky_runtime.launch: vae_robot_type:=ground
base_runtime.launch: uav_vae_robot_type:=ground ugv_vae_robot_type:=ground husky_vae_robot_type:=ground
```

This matches the current Super-LIO `velodyne_16.launch` path used by the three
robots. If a UAV is changed back to an Ouster 64 model, the UAV encoder and
every UAV decoder must be changed together:

```bash
roslaunch mrm_run_launch uav_runtime.launch vae_robot_type:=aerial
roslaunch mrm_run_launch base_runtime.launch uav_vae_robot_type:=aerial
```

In the UAV simulation, the mapping pipeline uses Super-LIO odometry by default:

```text
odom_topic=/lio/odom
imu_topic=/mavros/imu/data
cloud_body_topic=/lio/cloud_body
```

This keeps the local pose and body-frame scan paired from the same SLAM source.
PX4/MAVROS may need extra startup time before Super-LIO initializes; until then
`/lio/odom` and `/keyframe_vae` can be quiet. To temporarily test the PX4/MAVROS
pose fallback, override `odom_topic:=/mavros/local_position/odom` in
`uav_runtime.launch` or set `UAV_ODOM_TOPIC=/mavros/local_position/odom` before
running `run/run_mrm.sh`.

Initial pose is centralized in `/home/nlg/all_ws/run/lib/config.sh` for
`run_mrm.sh`:

```bash
UAV_SPAWN_X=0
UAV_SPAWN_Y=0
UAV_SPAWN_Z=0.5
UAV_SPAWN_YAW=0

UGV_SPAWN_X=1
UGV_SPAWN_Y=0
UGV_SPAWN_Z=0.5
UGV_SPAWN_YAW=0

HUSKY_SPAWN_X=2
HUSKY_SPAWN_Y=0
HUSKY_SPAWN_Z=0.5
HUSKY_SPAWN_YAW=0
```

`UAV_MAP_X/Y`, `UGV_MAP_X/Y`, and `HUSKY_MAP_X/Y` default to the corresponding
spawn `X/Y`, so changing the spawn location keeps Gazebo and LAMP/RViz aligned.
`MAP_Z` defaults to `0` because the Gazebo spawn height is a physical model
height, not usually a LAMP map offset.

For manual `mrm_run_launch` use, pass the same pose through `spawn_*` args:

```bash
roslaunch mrm_run_launch uav_runtime.launch spawn_x:=0 spawn_y:=0 spawn_z:=0.5 spawn_yaw:=0
roslaunch mrm_run_launch ugv_runtime.launch spawn_x:=1 spawn_y:=0 spawn_z:=0.5 spawn_yaw:=0
roslaunch mrm_run_launch husky_runtime.launch spawn_x:=2 spawn_y:=0 spawn_z:=0.5 spawn_yaw:=0
```

For UGV, start `ugv_gazebo.launch` before `ugv_runtime.launch`. Jackal needs
Gazebo's `/gazebo/spawn_urdf_model` service to exist before it spawns.

For Husky, `husky_runtime.launch` starts its own Gazebo by default. Leave
`run_gazebo:=true` unless you manually started a Husky Gazebo instance on the
same Husky ROS master and Gazebo master.

For UAV, `uav_runtime.launch` starts its own Gazebo by default through
`uav_sim_mocha.launch`. Leave `run_gazebo:=true` unless you manually started a
UAV Gazebo instance on the same UAV ROS master and Gazebo master.

Show Gazebo GUI:

```bash
roslaunch mrm_run_launch ugv_gazebo.launch gazebo_gui:=true
roslaunch mrm_run_launch uav_runtime.launch gazebo_gui:=true
roslaunch mrm_run_launch husky_runtime.launch gazebo_gui:=true
```

Use a different world:

```bash
roslaunch mrm_run_launch ugv_gazebo.launch \
  sim_world_file:=/absolute/path/to/world.world

roslaunch mrm_run_launch uav_runtime.launch \
  sim_world_file:=/absolute/path/to/world.world

roslaunch mrm_run_launch husky_runtime.launch \
  sim_world_file:=/absolute/path/to/world.world
```

Enable range image visualization:

```bash
roslaunch mrm_run_launch ugv_runtime.launch run_range_image_visualizer:=true
roslaunch mrm_run_launch uav_runtime.launch run_range_image_visualizer:=true
roslaunch mrm_run_launch husky_runtime.launch run_range_image_visualizer:=true
```

Then view:

```bash
rqt_image_view /range_image_viz/input_mono8
rqt_image_view /range_image_viz/output_mono8
rqt_image_view /range_image_viz/difference_mono8
```

## Config Files

Static YAML equivalents of the files generated by `run_mrm.sh`:

```text
config/robot_configs_centralized.yaml
config/robot_configs_distributed.yaml
config/lamp_robot_names.yaml
config/rssi_parameters.yaml
```

`robot_configs_centralized.yaml` includes Mocha names `basestation`, `jackal`,
`none_iris`, and `husky`.

`robot_configs_distributed.yaml` includes Mocha names `jackal`, `none_iris`,
and `husky`. LAMP names are listed separately in `lamp_robot_names.yaml` as
`jackal1`, `none_iris2`, and `husky3`.

## Recheck

Resolve launch XML without starting runtime nodes:

```bash
source /home/nlg/all_ws/devel/setup.bash
source /usr/share/gazebo/setup.bash
source $HOME/PX4-Autopilot/Tools/simulation/gazebo-classic/setup_gazebo.bash \
  $HOME/PX4-Autopilot \
  $HOME/PX4-Autopilot/build/px4_sitl_default
export ROS_PACKAGE_PATH=$HOME/PX4-Autopilot:$ROS_PACKAGE_PATH
export ROS_PACKAGE_PATH=$HOME/PX4-Autopilot/Tools/simulation/gazebo-classic/sitl_gazebo-classic:$ROS_PACKAGE_PATH

roslaunch mrm_run_launch base_runtime.launch --files \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_centralized.yaml
roslaunch mrm_run_launch ugv_gazebo.launch --files
roslaunch mrm_run_launch ugv_runtime.launch --files \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_distributed.yaml \
  run_distributed_lamp:=true
roslaunch mrm_run_launch husky_runtime.launch --files \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_distributed.yaml \
  run_distributed_lamp:=true \
  run_cmu_planner:=false
roslaunch mrm_run_launch uav_runtime.launch --files \
  robot_configs:=$(rospack find mrm_run_launch)/config/robot_configs_distributed.yaml \
  run_distributed_lamp:=true
roslaunch mrm_run_launch visual_tools.launch --files
```

`--files` and `--nodes` only resolve launch XML. They do not start Gazebo, PX4,
LAMP, MOCHA, RViz, or any other runtime node.
