#!/usr/bin/env python3
"""
verify_color_pipeline.py — RGB vs BGR Color Diagnostics

Usage (with the simulation running and /rgb topic active):
    python3 verify_color_pipeline.py

Generates 4 test images in <project_root>/tmp/ for visual comparison:
  1. raw_rgb8.png       — Image decoded with encoding='rgb8', saved WITHOUT conversion
  2. raw_bgr8.png       — Image decoded with encoding='bgr8', saved WITHOUT conversion
  3. pipeline_saved.jpg — Exactly as episode_generator_picking saves it (rgb8 -> cvtColor -> imwrite)
  4. pipeline_loaded.png — Exactly as training loads it (PIL.Image.open -> ToTensor -> back to image)

If colors are correct:
  - raw_rgb8.png and pipeline_loaded.png should look IDENTICAL with natural colors
  - raw_bgr8.png should show Red and Blue INVERTED
  - pipeline_saved.jpg should look with natural colors (same as raw_rgb8.png)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import os
import numpy as np


class ColorVerifier(Node):
    def __init__(self):
        super().__init__('color_verifier')
        self.bridge = CvBridge()
        self.received = False

        self.sub = self.create_subscription(Image, '/rgb', self.callback, 1)
        self.get_logger().info('Waiting for image on /rgb topic ...')

    def callback(self, msg):
        if self.received:
            return
        self.received = True

        script_dir = os.path.dirname(os.path.abspath(__file__))
        out_dir = os.path.join(script_dir, 'tmp')
        os.makedirs(out_dir, exist_ok=True)

        # === ROS message info ===
        self.get_logger().info(f'/rgb topic encoding: "{msg.encoding}"')
        self.get_logger().info(f'Resolution: {msg.width}x{msg.height}')
        self.get_logger().info(f'Step (bytes per row): {msg.step}')

        # === 1. Decode as rgb8 (what episode_generator_picking uses) ===
        img_rgb8 = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')
        # Save with PIL (which expects RGB) so colors look correct
        from PIL import Image as PILImage
        pil_rgb = PILImage.fromarray(img_rgb8)
        pil_rgb.save(os.path.join(out_dir, '1_raw_rgb8.png'))
        self.get_logger().info(f'[1] raw_rgb8.png: First 3 pixels (R,G,B) = {img_rgb8[48, 48, :]}')

        # === 2. Decode as bgr8 (what was used BEFORE) ===
        img_bgr8 = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        # Save with PIL (interprets as RGB, but bytes are BGR -> inverted colors)
        pil_bgr = PILImage.fromarray(img_bgr8)
        pil_bgr.save(os.path.join(out_dir, '2_raw_bgr8.png'))
        self.get_logger().info(f'[2] raw_bgr8.png: First 3 pixels (B,G,R) = {img_bgr8[48, 48, :]}')

        # === 3. Simulate episode_generator_picking save pipeline ===
        img_for_save = cv2.resize(img_rgb8, (96, 96))
        save_path = os.path.join(out_dir, '3_pipeline_saved.jpg')
        cv2.imwrite(save_path, cv2.cvtColor(img_for_save, cv2.COLOR_RGB2BGR))
        self.get_logger().info(f'[3] pipeline_saved.jpg: Saved with rgb8 -> cvtColor(RGB2BGR) -> imwrite')

        # === 4. Simulate training load pipeline (PIL -> ToTensor) ===
        import io
        import torch
        from torchvision import transforms

        # Read the JPG exactly as save_parquet + hf_transform_to_torch does
        pil_loaded = PILImage.open(save_path)
        to_tensor = transforms.ToTensor()
        tensor_img = to_tensor(pil_loaded)  # (3, H, W) float32 in [0, 1]

        # Convert back to numpy for saving and comparison
        np_img = (tensor_img.permute(1, 2, 0).numpy() * 255).astype(np.uint8)
        pil_final = PILImage.fromarray(np_img)
        pil_final.save(os.path.join(out_dir, '4_pipeline_loaded.png'))
        self.get_logger().info(f'[4] pipeline_loaded.png: PIL.open(jpg) -> ToTensor -> back to image')
        self.get_logger().info(f'    Tensor shape: {tensor_img.shape}, dtype: {tensor_img.dtype}')
        self.get_logger().info(f'    Pixel [48,48] (R,G,B) float = {tensor_img[:, 48, 48].tolist()}')

        # === 5. Simulate inference pipeline (pick_screwdriver) ===
        img_inference = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')
        img_inference = cv2.resize(img_inference, (96, 96))
        tensor_inference = torch.from_numpy(img_inference).to(torch.float32).permute(2, 0, 1) / 255
        self.get_logger().info(f'[5] Inference: Pixel [48,48] (R,G,B) float = {tensor_inference[:, 48, 48].tolist()}')

        # === Final comparison ===
        diff = torch.abs(tensor_img - tensor_inference).max().item()
        self.get_logger().info(f'')
        self.get_logger().info(f'========== RESULT ==========')
        self.get_logger().info(f'Max difference training vs inference: {diff:.6f}')
        if diff < 0.01:
            self.get_logger().info(f'✅ COLORS CONSISTENT — Pipeline is correct')
        else:
            self.get_logger().error(f'❌ COLORS INCONSISTENT — Channel mismatch detected')

        self.get_logger().info(f'')
        self.get_logger().info(f'Images saved in {out_dir}/')
        self.get_logger().info(f'  1_raw_rgb8.png       -> Should look with NATURAL colors')
        self.get_logger().info(f'  2_raw_bgr8.png       -> Should look with Red/Blue INVERTED')
        self.get_logger().info(f'  3_pipeline_saved.jpg  -> Should look with NATURAL colors')
        self.get_logger().info(f'  4_pipeline_loaded.png -> Should look IDENTICAL to 1 and 3')
        self.get_logger().info(f'')
        self.get_logger().info(f'Open the images and compare visually.')

        rclpy.shutdown()


def main():
    rclpy.init()
    node = ColorVerifier()
    rclpy.spin(node)


if __name__ == '__main__':
    main()
