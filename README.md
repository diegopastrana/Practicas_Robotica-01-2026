# TFM - Análisis de ciberseguridad en sistemas multi-robot con ROS2

**Máster Universitario en Investigación en Ciberseguridad**  
**Universidad de León**  
**Tutor:** Francisco Javier Rodríguez Lera

## Descripción

Este repositorio documenta la configuración y puesta en marcha de un sistema multi-robot basado en dos TurtleBot3 Burger conectados en red mediante ROS2 Humble, orientado al estudio de la toma de decisiones y la ciberseguridad en sistemas robóticos distribuidos.

---

## Hardware utilizado

| Componente | Descripción |
|---|---|
| Robots | 2x TurtleBot3 Burger |
| Controlador | Raspberry Pi 3 (por robot) |
| Placa de control | OpenCR |
| LiDAR | HLS-LFCD LDS-01 |
| PC | HP Pavilion Gaming 16 (Ubuntu 24.04, GPU GTX 1650 Ti) |

---

## Software y versiones

| Software | Versión |
|---|---|
| Ubuntu (TurtleBots) | 22.04.5 LTS |
| Ubuntu (PC) | 24.04 |
| ROS2 (TurtleBots) | Humble Hawksbill |
| ROS2 (PC) | Humble via Docker |
| Imagen base | ROBOTIS TurtleBot3 oficial |
| Docker | 29.3.0 |
| Ollama | 0.24.0 |
| CAI Framework | 0.5.10 |

---

## Configuración de los TurtleBots

### Imagen base
Se utilizó la imagen oficial de ROBOTIS para TurtleBot3 con ROS2 Humble preinstalado, siguiendo la guía:  
https://emanual.robotis.com/docs/en/platform/turtlebot3/sbc_setup/

### Variables de entorno (`.bashrc` de cada robot)

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=30 #TURTLEBOT3
export LDS_MODEL=LDS-01
export TURTLEBOT3_MODEL=burger
```

### IPs de los robots

| Robot | Hostname | IP |
|---|---|---|
| Bot1 (pegatina) | TurtleBot3-RaspberryPi | 10.174.101.98 |
| Bot2 | TurtleBot3-RaspberryPi3-2 | 10.174.101.12 |

### Acceso SSH

```bash
ssh practicasrobotica-02-2026@10.174.101.98  # Bot1
ssh practicasrobotica-02-2026@10.174.101.12  # Bot2
```

### Configuración OpenCR (Bot1)
El firmware de la OpenCR del Bot1 fue actualizado mediante el siguiente procedimiento:

```bash
sudo dpkg --add-architecture armhf
sudo apt-get update
sudo apt-get install libc6:armhf

export OPENCR_PORT=/dev/ttyACM0
export OPENCR_MODEL=burger
rm -rf ./opencr_update.tar.bz2
wget https://github.com/ROBOTIS-GIT/OpenCR-Binaries/raw/master/turtlebot3/ROS2/latest/opencr_update.tar.bz2
tar -xvf opencr_update.tar.bz2
cd ./opencr_update
./update.sh $OPENCR_PORT $OPENCR_MODEL.opencr
```

---

## Configuración del PC

### ROS2 Humble via Docker

Dado que el PC tiene Ubuntu 24.04 con ROS2 Jazzy, y los TurtleBots usan Humble (versiones incompatibles entre sí), se utiliza Docker para correr Humble en el PC.

```bash
docker pull osrf/ros:humble-desktop
```

#### Lanzar el contenedor

```bash
docker run -it \
  --network host \
  --name ros_humble \
  -e ROS_DOMAIN_ID=30 \
  osrf/ros:humble-desktop \
  bash
```

#### Reconectar al contenedor existente

```bash
docker start -i ros_humble
```

#### Dentro del contenedor

```bash
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-01
```

#### Instalar paquetes TurtleBot3 en el contenedor

```bash
apt update && apt install -y ros-humble-turtlebot3 ros-humble-turtlebot3-teleop
```

---

## Sistema multi-robot con namespaces

Para operar los dos robots simultáneamente sin interferencias, se asigna un namespace diferente a cada robot en el bringup.

### Lanzar bringup con namespace

**Bot1:**
```bash
source ~/.bashrc
ros2 launch turtlebot3_bringup robot.launch.py namespace:=tb3_0
```

**Bot2:**
```bash
source ~/.bashrc
ros2 launch turtlebot3_bringup robot.launch.py namespace:=tb3_1
```

### Topics resultantes

Con ambos robots activos, los topics quedan separados por namespace:

```
/tb3_0/cmd_vel    /tb3_1/cmd_vel
/tb3_0/scan       /tb3_1/scan
/tb3_0/odom       /tb3_1/odom
/tb3_0/imu        /tb3_1/imu
...
```

### Teleoperación independiente desde el PC

Abrir dos terminales con el contenedor Docker activo:

```bash
# Terminal 1 - Bot1
docker exec -it ros_humble bash
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 run turtlebot3_teleop teleop_keyboard --ros-args -r __ns:=/tb3_0

# Terminal 2 - Bot2
docker exec -it ros_humble bash
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 run turtlebot3_teleop teleop_keyboard --ros-args -r __ns:=/tb3_1
```

---

## Herramienta de ciberseguridad: CAI (Alias Robotics)

Repositorio: https://github.com/aliasrobotics/cai

### Instalación

```bash
python3 -m venv ~/cai_env
source ~/cai_env/bin/activate
pip install cai-framework
```

### Modelo local con Ollama (alternativa gratuita)

```bash
# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Descargar modelo
ollama pull llama3.1:8b

# Lanzar CAI con modelo local y permisos para captura de tráfico
sudo -E env PATH=$PATH CAI_MODEL=ollama/llama3.1:8b OPENAI_API_KEY=<api_key> cai
```

### Instalar tshark (necesario para análisis de tráfico)

```bash
sudo apt install tshark -y
```

### Agentes relevantes para el TFM

| Agente | Uso |
|---|---|
| `network_security_analyzer_agent` | Análisis de tráfico ROS2 |
| `redteam_agent` | Simulación de ataques |
| `blueteam_agent` | Defensa y monitorización |
| `replay_attack_agent` | Ataques de replay en red |

---

## Referencias

- [ROBOTIS TurtleBot3 e-Manual](https://emanual.robotis.com/docs/en/platform/turtlebot3/)
- [ROS2 Humble Documentation](https://docs.ros.org/en/humble/)
- [CAI Framework - Alias Robotics](https://github.com/aliasrobotics/cai)
- [Multi-TurtleBot3 Gazebo ROS2](https://github.com/Taeyoung96/Multi-turtlebot3-Gazebo-ROS2)
