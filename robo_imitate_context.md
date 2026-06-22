# Contexto de Implementación: Proyecto robo_imitate (Imitation Learning)

## 1. Información General del Entorno
* **Objetivo:** Ejecutar, entrenar y evaluar una *Diffusion Policy* para el brazo robótico Lite 6 utilizando el repositorio [MarijaGolubovic/robo_imitate](https://github.com/MarijaGolubovic/robo_imitate).
* **Hardware Anfitrión (Host):**
  * OS: Ubuntu 24.04 x86_64
  * CPU: 13th Gen Intel Core i9-13950HX (32 hilos)
  * RAM: 32 GB
  * GPU: NVIDIA GeForce RTX 4060 Max-Q (8 GB VRAM)
* **Requisitos Previos Cumplidos:**
  * Docker y NVIDIA Container Toolkit instalados y configurados correctamente.
  * **Cuenta activa en NVIDIA Developer Program** (Requerida para descargar la imagen de Isaac Sim).

---

## 2. Estado Actual y Logros (Pipeline Resuelto)

Se ha corregido exitosamente el "Dependency Hell" del repositorio original. Todo el proyecto está estructurado para ejecutarse estrictamente mediante contenedores Docker.

### Fase A: Entrenamiento del Modelo (Completado)
* **Archivo de configuración corregido:** `Dockerfile` (raíz).
* **Problemas resueltos:**
  * Incompatibilidad del ABI de NumPy 2.x con PyTorch precompilado.
  * Incompatibilidad de `diffusers` con aceleradores XPU (Intel) en un entorno CUDA.
  * Desaprobación de la función `cached_download` en `huggingface_hub`.
* **Solución aplicada (Version Pinning estricto):**
  Se modificó la capa de dependencias en el Dockerfile para anclar:
  `'numpy<2.0.0'`
  `'diffusers==0.27.2'`
  `'huggingface-hub==0.25.2'`
* **Estado:** El modelo se entrenó con éxito por 1000 épocas. Los archivos de pesos (`model.safetensors` y `config.json`) se encuentran en `~/Documents/gits/robo_imitate/imitation/outputs/train/`.

### Fase B: Inferencia y Controlador ROS 2 (Configurado)
* **Archivo de configuración corregido:** `docker/Dockerfile.pc`.
* **Problema resuelto:** Falla en la compilación de `colcon` por ausencia de la dependencia `ros-testing`.
* **Solución aplicada:** Se agregó el flag `--cmake-args -DBUILD_TESTING=OFF` en la compilación de los paquetes de ROS 2.
* **Comandos probados:** `make build-pc`, `make run`, `make exec`.
* **Estado:** El controlador `xarm_bringup` (ROS 2) está listo para operar, pero requiere la retroalimentación de Isaac Sim para levantar los controladores y publicar TFs en RViz2.

---

## 3. El Desafío Actual: Simulación con NVIDIA Isaac Sim

Para cerrar el bucle y evaluar la inferencia del modelo, es mandatorio conectar el controlador de ROS 2 con el simulador Isaac Sim.

* **El Problema Descubierto:** Intentar utilizar la imagen de Docker `nvcr.io/nvidia/isaac-sim:6.0.0` (Isaac Lab) arroja un error crítico (`ModuleNotFoundError: No module named 'rclpy'`). Esto sucede porque NVIDIA cambió radicalmente la inicialización del *ROS 2 Bridge* en sus versiones recientes. El script original del repositorio (`episode_generator_picking`) fue escrito para la API antigua de 2023.

### Siguientes Pasos (Para el Agente de Programación)

**Objetivo Inmediato:** Levantar el entorno de simulación Isaac Sim versión `2023.1.1` mediante Docker y establecer la conexión DDS (Red ROS 2) con el contenedor del controlador.

1. **Descargar y Ejecutar Isaac Sim 2023.1.1 (Docker):**
   *(Dado que el usuario ya posee cuenta en NVIDIA Developers, está autorizado a descargar esta imagen).*
   ```bash
   docker pull nvcr.io/nvidia/isaac-sim:2023.1.1
   
   docker run --name isaac-sim --entrypoint bash -it --gpus all -e "ACCEPT_EULA=Y" --rm --network=host \
       -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix \
       -v ~/Documents/gits/robo_imitate:/workspace/robo_imitate \
       nvcr.io/nvidia/isaac-sim:2023.1.1