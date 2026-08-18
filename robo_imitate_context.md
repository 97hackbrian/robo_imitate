# Implementation Context: robo_imitate Project (Imitation Learning)

## 1. General Environment Information
* **Objective:** Run, train, and evaluate a *Diffusion Policy* for the Lite 6 robotic arm using the [MarijaGolubovic/robo_imitate](https://github.com/MarijaGolubovic/robo_imitate) repository.
* **Host Hardware:**
  * OS: Ubuntu 24.04 x86_64
  * CPU: 13th Gen Intel Core i9-13950HX (32 threads)
  * RAM: 32 GB
  * GPU: NVIDIA GeForce RTX 4060 Max-Q (8 GB VRAM)
* **Prerequisites Met:**
  * Docker and NVIDIA Container Toolkit installed and correctly configured.
  * **Active NVIDIA Developer Program account** (required to download Isaac Sim image).

---

## 2. Current State & Achievements (Resolved Pipeline)

The original repository's "Dependency Hell" has been fully resolved. The entire project is structured to run strictly via Docker containers.

### Phase A: Model Training (Completed)
* **Fixed config file:** `Dockerfile` (root).
* **Resolved issues:**
  * NumPy 2.x ABI incompatibility with precompiled PyTorch.
  * `diffusers` incompatibility with XPU (Intel) accelerators in a CUDA environment.
  * Deprecation of `cached_download` in `huggingface_hub`.
* **Applied solution (strict version pinning):**
  `'numpy<2.0.0'`, `'diffusers==0.27.2'`, `'huggingface-hub==0.25.2'`
* **Status:** Model trained successfully. Weight files (`model.safetensors` and `config.json`) are in `~/Documents/gits/robo_imitate/imitation/outputs/train/`.

### Phase B: Inference and ROS 2 Controller (Configured)
* **Fixed config file:** `docker/Dockerfile.pc`.
* **Resolved issue:** `colcon` build failure due to missing `ros-testing` dependency.
* **Applied solution:** Added `--cmake-args -DBUILD_TESTING=OFF` flag.
* **Status:** The `xarm_bringup` controller (ROS 2) is ready to operate, connected to Isaac Sim 4.2.0.

### Phase C: Deep Debugging & Optimization (Completed)
* **Blind Movement Problem:** Robot ignored camera and blindly repeated the same trajectory. Diagnosis: *Posterior Collapse (State Overfitting)*.
* **Architectural Solution:** Disconnected `observation.state` from the Diffusion Policy's global conditioning in `diffusion_policy.py`. This forces the neural network to rely exclusively on the camera image for computing relative deltas.
* **Simulation Bug Fixed:** Patched `pick_screwdriver.py` (`--sim`) where an empty `Twist()` message caused the screwdriver to always spawn statically at `(0.35, 0.10)`. Added random generation to match the training distribution.
* **Extreme Performance Optimization:**
  * Rewrote training pipeline (later moved dataset caching from GPU back to CPU to prevent VRAM overflow on 8GB card).
  * Enabled PyTorch hardware optimizations (TF32, `cudnn.benchmark`) and AMP `bfloat16` (`torch.autocast`).
  * Implemented `CosineAnnealingLR` scheduler, gradient clipping (`max_norm=10.0`), and dynamically scaled learning rate.
  * Enabled `IMAGENET1K_V1` pre-trained weights for ResNet-18.

### Phase D: Speed & Reactivity Tuning (Current)
* **Problem:** After switching from 10Hz to 20Hz dataset (fps=20), the robot appeared to move in slow-motion because each predicted delta covers half the distance.
* **Solution:** Added a `speed_multiplier` (currently `40.0`) in `pick_screwdriver` that scales the predicted action deltas at runtime, restoring physical movement speed without retraining.
* **`n_action_steps` tuning:** Increased from 4 to 14 (max allowed is `horizon - n_obs_steps + 1 - 1 = 14`) for smoother, less jerky execution between replanning steps.
* **`num_inference_steps`:** Set to 12 (overridden post-load in `inference.py` line 21) — a balance between action quality and control-loop budget.

---

## 3. Current Parameter State

| Parameter | Value | Location |
|---|---|---|
| `n_obs_steps` | 2 | `config.py` |
| `horizon` | 16 | `config.py` |
| `n_action_steps` | 14 | `config.py` |
| `num_inference_steps` | 12 | `inference.py` (overrides config) |
| `speed_multiplier` | 40.0 | `pick_screwdriver` (runtime) |
| `timer_freq` | 0.05s (20Hz) | `pick_screwdriver` |
| `fps` (dataset) | 20 | `dataset.py` |
| `trigger_z` | 0.135 m | `pick_screwdriver` |
| `final_grasp_z` | 0.085 m | `pick_screwdriver` (GO_CLOSE state) |
| `max_episode_steps` | 1500 (sim) / 1600 (real) | `pick_screwdriver` |
| `image_size` | 256×256 | `config.py` / `pick_screwdriver` |
| `crop_shape` | 224×224 | `config.py` |
| `noise_scheduler` | DDIM | `config.py` |

---

## 4. Simulation: NVIDIA Isaac Sim (Resolved)

* **Image:** `nvcr.io/nvidia/isaac-sim:4.2.0` (NGC)
* **ROS 2 Bridge:** Manually installed `ros-humble-ros-base` inside the container.
* **Scene:** `xarm_bringup/isaac/object_picking.usda`
* **Key Topics:** `/isaac/joint_states`, `/isaac/joint_command`, `/rgb`, `/tf`, `/respawn`

---

## 5. Monitoring & Visualization

### Post-Run Plots (saved after each inference run)
Located in `imitation/outputs/results/<timestamp>/`:
* **`summary.png`** — 2×2 grid with:
  * Top-Left: Top-down X-Y trajectory (observed path + commanded targets + error line)
  * Top-Right: Z-height descent profile with trigger height line
  * Bottom-Left: Inference latency histogram with budget line
  * Bottom-Right: Text stats panel (steps, error, latency, config params)
* **`run_metrics.csv`** — Per-run metrics
* **`global_metrics.csv`** — Accumulated metrics across all runs

### Real-Time Dashboard (live during inference)
* **ROS 2 topic:** `/inference_dashboard/compressed` (CompressedImage, JPEG)
* **Update rate:** ~2 Hz (every 10 control ticks)
* **View with:** `rqt_image_view` or `ros2 run image_view image_view --ros-args -r image:=/inference_dashboard/compressed`
* **Contents:** 2×2 live grid showing X-Y trajectory, Z-height, rolling latency bars, and real-time stats

### 3D Trajectory Plots
* Saved to `action_trajectoris/sim/` or `action_trajectoris/real/` when max_episode_steps is exceeded.
* Shows observation vs. action trajectories in 3D space.

---

## 6. Key File Map

| File | Purpose |
|---|---|
| `imitation/pick_screwdriver` | Main inference script — executes Diffusion Policy, controls robot, saves metrics, publishes dashboard |
| `imitation/common/config.py` | DiffusionConfig dataclass (all hyperparameters) |
| `imitation/common/inference.py` | Model loading & single-step inference wrapper |
| `imitation/common/diffusion_policy.py` | Full Diffusion Policy architecture (UNet, DDIM, ResNet encoder) |
| `imitation/common/dataset.py` | LeRobotDataset — parquet loader with delta timestamps |
| `imitation/common/utils.py` | Utility functions including 3D trajectory plotting |
| `imitation/train_script` | Training script (DataLoader, CosineAnnealingLR, checkpointing) |
| `imitation/compute_stats` | Compute dataset normalization statistics |
| `xarm_bringup/scripts/episode_generator_picking` | Heuristic data collection — automated pick demonstrations |
| `xarm_bringup/scripts/episode_recorder` | Records episodes (images + observations) |
| `xarm_bringup/scripts/save_parquet` | Converts recorded episodes to parquet format |
| `verify_color_pipeline.py` | RGB vs BGR color diagnostics tool |
| `fix_actions.py` | Recalculates action files from observations |