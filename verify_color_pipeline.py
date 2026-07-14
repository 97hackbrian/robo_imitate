#!/usr/bin/env python3
"""
verify_color_pipeline.py — Diagnóstico de color RGB vs BGR

Uso (con la simulación corriendo y el tópico /rgb activo):
    python3 verify_color_pipeline.py

Genera 4 imágenes de prueba en /tmp/color_test/ para comparación visual:
  1. raw_rgb8.png       — Imagen decodificada con encoding='rgb8', guardada SIN conversión
  2. raw_bgr8.png       — Imagen decodificada con encoding='bgr8', guardada SIN conversión
  3. pipeline_saved.jpg — Exactamente como episode_generator_picking la guarda (rgb8 → cvtColor → imwrite)
  4. pipeline_loaded.png — Exactamente como el training la carga (PIL.Image.open → ToTensor → de vuelta a imagen)

Si los colores son correctos:
  - raw_rgb8.png y pipeline_loaded.png deben verse IGUALES y con colores naturales
  - raw_bgr8.png debe verse con Rojo y Azul INVERTIDOS
  - pipeline_saved.jpg debe verse con colores naturales (igual que raw_rgb8.png)
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
        self.get_logger().info('Esperando imagen del tópico /rgb ...')

    def callback(self, msg):
        if self.received:
            return
        self.received = True

        script_dir = os.path.dirname(os.path.abspath(__file__))
        out_dir = os.path.join(script_dir, 'tmp')
        os.makedirs(out_dir, exist_ok=True)

        # === Info del mensaje ROS ===
        self.get_logger().info(f'Encoding del tópico /rgb: "{msg.encoding}"')
        self.get_logger().info(f'Resolución: {msg.width}x{msg.height}')
        self.get_logger().info(f'Step (bytes por fila): {msg.step}')

        # === 1. Decodificar como rgb8 (lo que usa episode_generator_picking) ===
        img_rgb8 = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')
        # Guardar con PIL (que espera RGB) para que se vea correcto
        from PIL import Image as PILImage
        pil_rgb = PILImage.fromarray(img_rgb8)
        pil_rgb.save(os.path.join(out_dir, '1_raw_rgb8.png'))
        self.get_logger().info(f'[1] raw_rgb8.png: Primeros 3 píxeles (R,G,B) = {img_rgb8[48, 48, :]}')

        # === 2. Decodificar como bgr8 (lo que se usaba ANTES) ===
        img_bgr8 = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        # Guardar con PIL (interpreta como RGB, pero los bytes son BGR → colores invertidos)
        pil_bgr = PILImage.fromarray(img_bgr8)
        pil_bgr.save(os.path.join(out_dir, '2_raw_bgr8.png'))
        self.get_logger().info(f'[2] raw_bgr8.png: Primeros 3 píxeles (B,G,R) = {img_bgr8[48, 48, :]}')

        # === 3. Simular el pipeline de guardado de episode_generator_picking ===
        img_for_save = cv2.resize(img_rgb8, (96, 96))
        save_path = os.path.join(out_dir, '3_pipeline_saved.jpg')
        cv2.imwrite(save_path, cv2.cvtColor(img_for_save, cv2.COLOR_RGB2BGR))
        self.get_logger().info(f'[3] pipeline_saved.jpg: Guardado con rgb8 → cvtColor(RGB2BGR) → imwrite')

        # === 4. Simular el pipeline de carga del training (PIL → ToTensor) ===
        import io
        import torch
        from torchvision import transforms

        # Leer el JPG exactamente como lo hace save_parquet + hf_transform_to_torch
        pil_loaded = PILImage.open(save_path)
        to_tensor = transforms.ToTensor()
        tensor_img = to_tensor(pil_loaded)  # (3, H, W) float32 en [0, 1]

        # Convertir de vuelta a numpy para guardar y comparar
        np_img = (tensor_img.permute(1, 2, 0).numpy() * 255).astype(np.uint8)
        pil_final = PILImage.fromarray(np_img)
        pil_final.save(os.path.join(out_dir, '4_pipeline_loaded.png'))
        self.get_logger().info(f'[4] pipeline_loaded.png: PIL.open(jpg) → ToTensor → back to image')
        self.get_logger().info(f'    Tensor shape: {tensor_img.shape}, dtype: {tensor_img.dtype}')
        self.get_logger().info(f'    Pixel [48,48] (R,G,B) float = {tensor_img[:, 48, 48].tolist()}')

        # === 5. Simular el pipeline de inferencia (pick_screwdriver) ===
        img_inference = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')
        img_inference = cv2.resize(img_inference, (96, 96))
        tensor_inference = torch.from_numpy(img_inference).to(torch.float32).permute(2, 0, 1) / 255
        self.get_logger().info(f'[5] Inferencia: Pixel [48,48] (R,G,B) float = {tensor_inference[:, 48, 48].tolist()}')

        # === Comparación final ===
        diff = torch.abs(tensor_img - tensor_inference).max().item()
        self.get_logger().info(f'')
        self.get_logger().info(f'========== RESULTADO ==========')
        self.get_logger().info(f'Max diferencia training vs inferencia: {diff:.6f}')
        if diff < 0.01:
            self.get_logger().info(f'✅ COLORES CONSISTENTES — El pipeline está correcto')
        else:
            self.get_logger().error(f'❌ COLORES INCONSISTENTES — Hay un mismatch de canales')

        self.get_logger().info(f'')
        self.get_logger().info(f'Imágenes guardadas en {out_dir}/')
        self.get_logger().info(f'  1_raw_rgb8.png      → Debe verse con colores NATURALES')
        self.get_logger().info(f'  2_raw_bgr8.png      → Debe verse con Rojo/Azul INVERTIDOS')
        self.get_logger().info(f'  3_pipeline_saved.jpg → Debe verse con colores NATURALES')
        self.get_logger().info(f'  4_pipeline_loaded.png → Debe verse IGUAL que 1 y 3')
        self.get_logger().info(f'')
        self.get_logger().info(f'Abre las imágenes y compara visualmente.')

        rclpy.shutdown()


def main():
    rclpy.init()
    node = ColorVerifier()
    rclpy.spin(node)


if __name__ == '__main__':
    main()
