# TFM - Análisis de ciberseguridad en sistemas multi-robot con ROS2

**Máster Universitario en Investigación en Ciberseguridad**  
**Universidad de León**  
**Tutor:** Francisco Javier Rodríguez Lera

## Descripción

Este repositorio documenta la configuración y puesta en marcha de un sistema multi-robot basado en dos TurtleBot3 Burger conectados en red mediante ROS2 Humble, orientado al estudio de la toma de decisiones y la ciberseguridad en sistemas robóticos distribuidos.

El proyecto implementa el framework de razonamiento normativo **Jiminy** para modelar la toma de decisiones de los robots en base a reglas lógicas, comparando el comportamiento en entornos mono-robot y multi-robot, e incorporando una dimensión de ciberseguridad mediante el análisis del tráfico DDS y la confianza en los datos compartidos entre robots.

---

## Hardware utilizado

| Componente | Descripción |
|---|---|
| Robots | 2x TurtleBot3 Burger |
| Controlador | Raspberry Pi 3B+ (por robot) |
| Placa de control | OpenCR |
| LiDAR | HLS-LFCD LDS-01 |
| PC de desarrollo | HP Pavilion Gaming 16 — Intel Core i7-10750H, 16 GB RAM, GTX 1650 Ti |
| Router | TP-Link AX1500 (red experimental dedicada) |

---

## Software y versiones

| Software | Versión |
|---|---|
| Ubuntu (TurtleBots) | 22.04.5 LTS |
| Ubuntu (PC) | 24.04 |
| ROS2 (TurtleBots) | Humble Hawksbill (nativo) |
| ROS2 (PC) | Humble via Docker (osrf/ros:humble-desktop) |
| Imagen base robots | ROBOTIS TurtleBot3 oficial |
| Docker | 29.3.0 |
| Jiminy Framework | jiminy_ros (github.com/jiminy-framework) |
| Ollama | 0.24.0 |
| CAI Framework | 0.5.10 |

---

## Configuración de los TurtleBots

### Imagen base
Se utilizó la imagen oficial de ROBOTIS para TurtleBot3 con ROS2 Humble preinstalado, siguiendo la guía:  
https://emanual.robotis.com/docs/en/platform/turtlebot3/sbc_setup/

### Variables de entorno (.bashrc de cada robot)

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
| Bot1 (pegatina) | TurtleBot3-RaspberryPi | 10.13.240.98 |
| Bot2 | TurtleBot3-RaspberryPi3-2 | 10.13.240.12 |

> Las IPs pueden cambiar según la red. Para encontrarlas usar: `nmap -sn 10.13.240.0/24`

### Acceso SSH

```bash
ssh practicasrobotica-02-2026@10.13.240.98   # Bot1
ssh practicasrobotica-02-2026@10.13.240.12   # Bot2
```

### Actualización firmware OpenCR (Bot1)

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

El PC usa Ubuntu 24.04 con ROS2 Jazzy (incompatible con Humble). Se utiliza Docker para ejecutar Humble:

```bash
docker pull osrf/ros:humble-desktop
```

#### Lanzar contenedor

```bash
docker run -it \
  --network host \
  --name ros_humble \
  -e ROS_DOMAIN_ID=30 \
  osrf/ros:humble-desktop \
  bash
```

#### Reconectar al contenedor

```bash
docker start -i ros_humble
```

#### Dentro del contenedor

```bash
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-01
```

#### Instalar paquetes TurtleBot3

```bash
apt update && apt install -y ros-humble-turtlebot3 ros-humble-turtlebot3-teleop
```

---

## Sistema multi-robot con namespaces

Para operar los dos robots simultáneamente sin interferencias se asigna un namespace diferente a cada robot en el bringup.

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

```
/tb3_0/cmd_vel    /tb3_1/cmd_vel
/tb3_0/scan       /tb3_1/scan
/tb3_0/odom       /tb3_1/odom
/tb3_0/imu        /tb3_1/imu
```

### Teleoperación independiente desde el PC

```bash
# Bot1
docker exec -it ros_humble bash
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 run turtlebot3_teleop teleop_keyboard --ros-args -r __ns:=/tb3_0

# Bot2
docker exec -it ros_humble bash
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 run turtlebot3_teleop teleop_keyboard --ros-args -r __ns:=/tb3_1
```

---

## Análisis de vulnerabilidades ROS2 (sin SROS2)

Se capturó y analizó el tráfico de red entre los robots para demostrar la vulnerabilidad de la comunicación DDS sin cifrado.

### Captura de tráfico

```bash
sudo tcpdump -i wlo1 -n -c 200 -w /tmp/ros2_capture.pcap
```

### Análisis de protocolos

```bash
sudo tshark -r /tmp/ros2_capture.pcap -q -z io,phs
```

**Resultado:**
```
Protocol Hierarchy Statistics
frame                    frames:200
  ip                     frames:196
    udp                  frames:143
      rtps               frames:82    <- Tráfico ROS2/DDS sin cifrar
      data               frames:53
    tcp                  frames:53
      tls                frames:28    <- Solo tráfico externo cifrado
```

### Análisis de paquetes RTPS

```bash
sudo tshark -r /tmp/ros2_capture.pcap -Y "rtps" -T fields \
  -e ip.src -e ip.dst -e udp.srcport -e udp.dstport
```

**Resultado:** Todo el tráfico DDS va en multicast UDP al puerto 14900 (239.255.0.1:14900) sin cifrado, con metadatos como PARTICIPANT_TYPE, enclave=/ y las IPs de los robots visibles en texto plano.

**Conclusión:** Sin SROS2, cualquier dispositivo en la misma red puede interceptar y manipular la comunicación entre robots.

---

## Jiminy Framework — Toma de decisiones normativa

### Instalación en los TurtleBots

```bash
cd ~/turtlebot3_ws/src
git clone https://github.com/jiminy-framework/jiminy_ros.git

# Dependencias
pip install empy==3.3.4
sudo apt install libreadline-dev -y

# Compilar
cd ~/turtlebot3_ws
colcon build --symlink-install --parallel-workers 1 \
  --packages-select jiminy_msgs jiminy_ros jiminy_bringup jiminy_terminal

source ~/.bashrc
```

### Escenario TurtleBot3

Se creó el escenario `turtlebot3_obstacle.yaml` con los siguientes hechos:

| ID | Descripción |
|---|---|
| w1 | Obstáculo a menos de 30 cm |
| w2 | Obstáculo entre 30 y 60 cm |
| w3 | Sin obstáculo en 60 cm |
| w4 | El robot está en movimiento |
| w5 | El peer reporta camino libre |
| w6 | El peer reporta obstáculo |
| w7 | Datos del peer fiables (autenticado) |
| w8 | Datos del peer no fiables (comprometido) |

### Lanzar Jiminy con el escenario

```bash
ros2 launch jiminy_bringup jiminy.launch.py config_file:=turtlebot3_obstacle.yaml
```

### Experimentos realizados

#### Caso 1 — Robot individual con obstáculo crítico

```bash
ros2 service call /call_jiminy jiminy_msgs/srv/CallJiminy \
  "{semantics: {semantics: 'priority'}, facts: ['w1', 'w4']}"
```
**Decisión:** `d_stop` (parar inmediatamente)

#### Caso 2 — Robot individual sin obstáculo

```bash
ros2 service call /call_jiminy jiminy_msgs/srv/CallJiminy \
  "{semantics: {semantics: 'priority'}, facts: ['w3', 'w4']}"
```
**Decisión:** `d_move` (seguir avanzando)

#### Caso 3 — Multi-robot: peer fiable detecta obstáculo

```bash
ros2 service call /call_jiminy jiminy_msgs/srv/CallJiminy \
  "{semantics: {semantics: 'priority'}, facts: ['w3', 'w4', 'w6', 'w7']}"
```
**Decisión:** `d_slow_down` — El robot no ve obstáculo propio pero ralentiza porque su peer de confianza sí lo detecta.

#### Caso 4 — Ciberseguridad: peer comprometido

```bash
ros2 service call /call_jiminy jiminy_msgs/srv/CallJiminy \
  "{semantics: {semantics: 'priority'}, facts: ['w3', 'w4', 'w6', 'w8']}"
```
**Decisión:** `d_move` + `d_ignore_peer` + `d_use_own_sensors` — El robot detecta que el peer está comprometido, ignora sus datos y decide solo con sus propios sensores.

### Resumen de experimentos

| Caso | Hechos | Decisión |
|---|---|---|
| Individual con obstáculo | w1, w4 | `d_stop` |
| Individual sin obstáculo | w3, w4 | `d_move` |
| Multi-robot peer fiable | w3, w4, w6, w7 | `d_slow_down` |
| Multi-robot peer comprometido | w3, w4, w6, w8 | `d_move` + `d_ignore_peer` |

---

## Nodo puente LiDAR-Jiminy

El nodo `lidar_jiminy_bridge.py` automatiza la toma de decisiones leyendo el LiDAR en tiempo real y llamando a Jiminy sin intervención manual.

### Instalación

```bash
cp lidar_jiminy_bridge.py ~/turtlebot3_ws/src/jiminy_ros/jiminy_ros/src/
cd ~/turtlebot3_ws
colcon build --symlink-install --parallel-workers 1 --packages-select jiminy_ros
chmod +x ~/turtlebot3_ws/install/jiminy_ros/lib/jiminy_ros/lidar_jiminy_bridge.py
```

### Lanzar en modo individual

```bash
ros2 run jiminy_ros lidar_jiminy_bridge.py --ros-args -p namespace:=tb3_0
```

### Lanzar en modo multi-robot

```bash
ros2 run jiminy_ros lidar_jiminy_bridge.py --ros-args \
  -p namespace:=tb3_0 \
  -p peer_namespace:=tb3_1 \
  -p peer_trusted:=true
```

### Ejemplo de salida en tiempo real

```
[INFO] Decision: d_stop    | dist=0.198m | facts=['w1', 'w4']
[INFO] Decision: d_move    | dist=1.020m | facts=['w3', 'w4']
[INFO] Decision: d_stop    | dist=0.203m | facts=['w1', 'w4']
[INFO] Decision: d_move    | dist=0.789m | facts=['w3', 'w4']
```

---

## Herramienta de ciberseguridad: CAI (Alias Robotics)

Repositorio: https://github.com/aliasrobotics/cai

### Instalación

```bash
python3 -m venv ~/cai_env
source ~/cai_env/bin/activate
pip install cai-framework
sudo apt install tshark -y
```

### Modelo local con Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b

sudo -E env PATH=$PATH \
  CAI_MODEL=ollama/llama3.1:8b \
  OPENAI_API_KEY=<api_key> \
  cai
```

### Agentes relevantes para el TFM

| Agente | Uso |
|---|---|
| `network_security_analyzer_agent` | Análisis de tráfico ROS2 |
| `redteam_agent` | Simulación de ataques |
| `blueteam_agent` | Defensa y monitorización |
| `replay_attack_agent` | Ataques de replay en red |

---

## Experimento multi-robot completo

Jiminy está instalado en ambos robots. Con los dos bots corriendo simultáneamente con sus respectivos namespaces, bringup, Jiminy y el nodo puente, se obtienen decisiones en tiempo real que incorporan la información compartida entre robots.

### Lanzar el sistema completo

**Bot1 (3 terminales SSH):**
```bash
# Terminal 1
source ~/.bashrc && ros2 launch turtlebot3_bringup robot.launch.py namespace:=tb3_0

# Terminal 2
source ~/.bashrc && ros2 launch jiminy_bringup jiminy.launch.py config_file:=turtlebot3_obstacle.yaml

# Terminal 3 — modo multi-robot con peer fiable
source ~/.bashrc && ros2 run jiminy_ros lidar_jiminy_bridge.py --ros-args \
  -p namespace:=tb3_0 -p peer_namespace:=tb3_1 -p peer_trusted:=true
```

**Bot2 (3 terminales SSH):**
```bash
# Terminal 4
source ~/.bashrc && ros2 launch turtlebot3_bringup robot.launch.py namespace:=tb3_1

# Terminal 5
source ~/.bashrc && ros2 launch jiminy_bringup jiminy.launch.py config_file:=turtlebot3_obstacle.yaml

# Terminal 6 — modo multi-robot con peer fiable
source ~/.bashrc && ros2 run jiminy_ros lidar_jiminy_bridge.py --ros-args \
  -p namespace:=tb3_1 -p peer_namespace:=tb3_0 -p peer_trusted:=true
```

### Verificar decisiones desde el PC

```bash
docker exec -it ros_humble bash
source /opt/ros/humble/setup.bash
ros2 topic echo /tb3_0/jiminy_decision
ros2 topic echo /tb3_1/jiminy_decision
```

### Ejemplo de salida modo multi-robot con peer fiable

```
data: d_slow_down | dist=0.520m | facts=['w2', 'w4', 'w6', 'w7'] | accepted=['d_prefer_safe', 'd_slow_down', 'i_caution', 'i_peer_danger']
data: d_stop      | dist=0.122m | facts=['w1', 'w4', 'w6', 'w7'] | accepted=['d_prefer_safe', 'd_stop', 'i_danger', 'i_peer_danger']
```

### Ejemplo de salida modo multi-robot con peer comprometido

```bash
# Relanzar nodo puente del bot1 con peer no fiable
ros2 run jiminy_ros lidar_jiminy_bridge.py --ros-args \
  -p namespace:=tb3_0 -p peer_namespace:=tb3_1 -p peer_trusted:=false
```

```
data: d_stop | dist=0.223m | facts=['w1', 'w4', 'w6', 'w8'] | accepted=['d_ignore_peer', 'd_prefer_safe', 'd_stop', 'd_use_own_sensors']
data: d_slow_down | dist=0.500m | facts=['w2', 'w4', 'w6', 'w8'] | accepted=['d_ignore_peer', 'd_prefer_safe', 'd_slow_down', 'd_use_own_sensors']
```

Con peer comprometido (`w8`), `d_ignore_peer` y `d_use_own_sensors` aparecen en las normas aceptadas, demostrando que el robot ignora los datos manipulados y decide únicamente con sus propios sensores.

---

## Trabajo pendiente

- Implementar SROS2 para autenticación y cifrado
- Comparar tráfico DDS con y sin SROS2
- Conectar SROS2 con Jiminy: peer autenticado → `w7`, no autenticado → `w8`
- Visualización con RViz en modo multi-robot

---

## Referencias

- [ROBOTIS TurtleBot3 e-Manual](https://emanual.robotis.com/docs/en/platform/turtlebot3/)
- [ROS2 Humble Documentation](https://docs.ros.org/en/humble/)
- [Jiminy Framework](https://github.com/jiminy-framework)
- [CAI Framework - Alias Robotics](https://github.com/aliasrobotics/cai)
- [Multi-TurtleBot3 Gazebo ROS2](https://github.com/Taeyoung96/Multi-turtlebot3-Gazebo-ROS2)
