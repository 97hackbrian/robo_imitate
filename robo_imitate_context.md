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

## 3. El Desafío Actual: Simulación con NVIDIA Isaac Sim (Resuelto)

Para cerrar el bucle y evaluar la inferencia del modelo, es mandatorio conectar el controlador de ROS 2 con el simulador Isaac Sim.

* **El Problema Descubierto:** Intentar utilizar versiones muy recientes de Isaac Sim (`6.0.0`) no funciona con el proyecto original debido a cambios masivos en OmniGraph y la falta de compatibilidad directa. Además, la versión `2023.1.1` original del proyecto fue eliminada del registro NGC.
* **La Solución:** Utilizar la imagen **`nvcr.io/nvidia/isaac-sim:4.2.0`**, la cual ofrece un equilibrio perfecto (OmniGraph estable y compatibilidad con ROS 2 Humble). Sin embargo, esta imagen carece de la instalación base de ROS 2 necesaria para el Bridge.

### Pasos para Configurar Isaac Sim 4.2.0 con ROS 2

**1. Lanzar el contenedor de Isaac Sim:**
```bash
docker run --name isaac-sim-4.2 --entrypoint bash -it --gpus all -e "ACCEPT_EULA=Y" --rm --network=host \
    -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v ~/Documents/gits/robo_imitate:/workspace/robo_imitate \
    nvcr.io/nvidia/isaac-sim:4.2.0
```

**2. Instalar ROS 2 Humble dentro del contenedor:**
Una vez dentro del contenedor como `root`, ejecuta el siguiente script para instalar la base de ROS 2 y habilitar el Bridge:
```bash
# Agregar llaves y repositorios de ROS 2
apt-get update && apt-get install -y curl software-properties-common
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Instalar ROS 2 base
apt-get update && apt-get install -y ros-humble-ros-base

# Activar ROS 2 en el entorno
source /opt/ros/humble/setup.bash

# Iniciar Isaac Sim
./runapp.sh
```

Con esto, los Action Graphs de Isaac Sim podrán comunicarse exitosamente con el `robo_imitate-container` a través de DDS.