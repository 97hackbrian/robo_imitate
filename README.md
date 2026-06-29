# Imitation learning with ROS 2


| ![Object picking in IsaacSim](./media/object_picking_sim.gif)  | ![Object picking in IsaacSim](./media/object_picking_random_move.gif) |
|:-------------------------------------------------------------------:|:----------------------------------------------------:|
| Object picking with imitation learning                         | Object picking when pose of object is randomized    |

<div align='center'>
	<img src="./media/robo_imitate.png">
</div>

</br>

<div>

The **RoboImitate** project supports imitation learning through a [**Diffusion Policy**](https://diffusion-policy.cs.columbia.edu/). This policy learns behavior using expert demonstrations. *(Stay tuned for our upcoming YouTube presentation for more details!)*


#### This repository allows you to:

- **Collect demonstrations** in simulated environments (Isaac Sim). [Learn more here](xarm_bringup/scripts/README.md).
- **Train and evaluate** a Diffusion Policy model. [Learn more here](imitation/README.md).

</div>

### 🚀 Recent Model & Training Improvements

1. **Fixed Posterior Collapse (State Overfitting)**
   - **Impact:** Critical
   - **Details:** Disconnected the `observation.state` (robot arm coordinates) from the Diffusion Policy's global conditioning. Previously, the network bypassed visual inputs and memorized coordinate transformations, causing the robot to blindly repeat the exact same movement. The policy is now strictly forced to rely on the camera image to detect and track the object.
2. **Fixed Simulation Randomization Bug**
   - **Impact:** High
   - **Details:** Fixed a critical bug in `pick_screwdriver.py` (`--sim` mode) where an empty `Twist()` message caused the screwdriver to always spawn at the exact same fallback coordinates `(0.35, 0.10)`. Added coordinate randomization that mirrors the training distribution, allowing inference tests to correctly evaluate visual tracking.
3. **Massive Training Speed & GPU VRAM Optimization**
   - **Impact:** High
   - **Details:** Rewrote the training pipeline to load the entire dataset directly into GPU VRAM at startup (`GPUDataset`), eliminating CPU-GPU transfer bottlenecks. Enabled PyTorch hardware optimizations (TF32, `cudnn.benchmark`) and `bfloat16` AMP (`torch.autocast`). This slashed VRAM usage by over 50% and increased training speed by >3x, allowing a massive batch size of 512.
4. **Learning Rate & Optimization Upgrades**
   - **Impact:** Medium
   - **Details:** Implemented a dynamic sqrt-scaled learning rate based on batch size. Added a `CosineAnnealingLR` scheduler and gradient clipping (`max_norm=10.0`) to ensure stable convergence.
5. **Leveraged Pre-trained Vision Backbone**
   - **Impact:** Medium
   - **Details:** Enabled `IMAGENET1K_V1` pre-trained weights for the ResNet-18 vision backbone in `config.py`. This significantly reduces the training time and dataset size required to learn robust visual features compared to training from scratch.


>[!IMPORTANT]  
You need to have Docker installed. If you have an Nvidia GPU, you need to additionally follow this [guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html). Additionally, you need to install Isaac-Sim if you want to use simulation. 

> **Note on Isaac Sim:** We recommend using `nvcr.io/nvidia/isaac-sim:4.2.0`. Because this image does not have ROS 2 pre-installed, you will need to manually install `ros-humble-ros-base` inside the container as `root` and source it before running `./runapp.sh`.

#### Install docker
```sh
sudo apt install git make curl
curl -sSL https://get.docker.com | sh && sudo usermod -aG docker $USER
```

### Installation
- Download our source code:
```sh
git clone https://github.com/MarijaGolubovic/robo_imitate.git && cd robo_imitate/docker
```

- Build docker container
```sh
make build-pc run exec
```
- Build ROS 2 packages
```sh
colcon build --symlink-install && source ./install/local_setup.bash
```

### Model evaluation
>[!NOTE] 
You can download pretrain model and aditional files from this [link](https://drive.google.com/drive/folders/1x2Mamae9xvImDJb821TEb221UaC_fTUV?usp=sharing). Downloaded model and files you need to put inside folder `imitation/outputs/train`. If folder don't exist you need to create it.

- Run Isaac-Sim Simulation

Inside the docker container run:
- Run ROS 2 controller
```sh
ros2 launch xarm_bringup lite6_cartesian_launch.py rviz:=false sim:=true
```
If you want to visualize the robot set `rviz` to true.

- Open another terminal and run docker
```sh
make exec
```

- Run model inference inside docker
```sh
 cd src/robo_imitate && python3 ./imitation/pick_screwdriver --sim
```

### Model training
Inside `robo_imitate` directory run follow commands:

```sh 
docker build --build-arg UID=$(id -u) -t imitation .
```

```sh
docker run -v $(pwd)/imitation/:/docker/app/imitation:Z --gpus all -it -e DATA_PATH=imitation/data/sim_env_data.parquet -e BATCH_SIZE=32 -e EPOCH=50000 imitation
```

>[!TIP]
 If you want to run model training inside docker, run this command inside the folder `src/robo_imitate`. Before that, you need to build the docker (see the [Installation](#installation) section for details).

```sh
python3 ./imitation/compute_stats --path imitation/data/sim_env_data.parquet
python3 ./imitation/train_script --path imitation/data/sim_env_data.parquet --batch_size 32 --epoch 50000
```

### Acknowledgment
- This project is done in collaboration with [@SpesRobotics](https://spes.ai/).
- Thanks to LeRobot team for open sourcing LeRobot projects. 
- Thanks to Cheng Chi, Zhenjia Xu and colleagues for open sourcing Diffusion policy

### Physical Implementation
| ![Object picking physics env](./media/pick_object.gif)  | ![Object picking physics env](./media/move_object.gif) |
|:-------------------------------------------------------------------:|:----------------------------------------------------:|
| Physical robot picking                                              | Physical robot moving                                |
