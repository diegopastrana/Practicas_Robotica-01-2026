# Análisis de la toma de decisiones y la ciberseguridad en sistemas multi-robot distribuidos basados en ROS 2

Repositorio asociado al Trabajo de Fin de Máster del Máster Universitario en Investigación en Ciberseguridad.

El proyecto estudia la seguridad y la resiliencia de un sistema multi-robot basado en ROS 2 Humble, utilizando dos TurtleBot3 Burger reales. El trabajo combina dos capas complementarias:

- **SROS 2 / DDS-Security**, para proteger las comunicaciones DDS mediante autenticación y cifrado.
- **Jiminy**, como framework normativo deóntico para razonar sobre la fiabilidad de la información recibida y tomar decisiones conservadoras ante datos no fiables.

La integración automática entre ambas capas no forma parte de la implementación final. En el prototipo desarrollado, el estado de confianza del peer se modela mediante un parámetro, quedando su derivación automática desde el estado real de DDS-Security como trabajo futuro.

## Objetivo del repositorio

Este repositorio recoge el material técnico desarrollado durante el TFM que se ha considerado publicable sin exponer información sensible del entorno experimental.

Actualmente incluye:

- escenarios normativos utilizados con Jiminy;
- código Python del nodo puente empleado en el experimento E5;
- documentación complementaria del entorno experimental;
- información sobre la captura y análisis de tráfico DDS.

No se incluyen capturas `.pcap`, claves privadas, keystores completos ni certificados sensibles.

## Entorno utilizado

El entorno experimental empleado en el trabajo fue el siguiente:

- Ubuntu 22.04
- ROS 2 Humble
- TurtleBot3 Burger
- Python 3
- SROS 2
- DDS-Security
- Jiminy / jiminy_ros
- Wireshark / tshark

## Estructura actual del repositorio

```text
.
├── README.md
├── .gitignore
├── src/
│   └── lidar_jiminy_bridgeE5.py
└── jiminy/
    ├── turtlebot3_obstacle.yaml
    ├── turtlebot3_lidar_attacked_peer.yaml
    └── turtlebot3_lidar_attacked_stop.yaml
```

## Código incluido

El archivo actualmente incluido en la carpeta `src/` es:

```text
src/lidar_jiminy_bridgeE5.py
```

Este nodo actúa como puente entre la información sensorial de ROS 2 y el modelo normativo de Jiminy en el escenario E5. Su función es transformar el estado observado del entorno y del peer en hechos normativos que permiten determinar la acción del robot.

En particular, este escenario representa una situación conservadora en la que ni el LiDAR propio ni el peer se consideran fuentes fiables, por lo que el sistema debe detener el robot aunque el peer indique que el camino está despejado.

## Escenarios Jiminy incluidos

La carpeta `jiminy/` contiene los escenarios normativos utilizados en los experimentos:

| Archivo | Uso en el TFM | Descripción |
|---|---|---|
| `turtlebot3_obstacle.yaml` | E1 y E2 | Escenario base de seguridad ante obstáculos. En E2 se reutiliza modificando el parámetro `distance_critical:=0.15` para demostrar configurabilidad en tiempo de ejecución sin recompilar. |
| `turtlebot3_lidar_attacked_peer.yaml` | E3 | Escenario con LiDAR propio comprometido y uso de información procedente del peer. |
| `turtlebot3_lidar_attacked_stop.yaml` | E5 | Escenario en el que ni el sensor propio ni el peer son fiables, activando una decisión conservadora de parada. |

## Casos de prueba

La validación experimental descrita en la memoria se estructuró en cinco casos de prueba:

| Caso | Material incluido en este repositorio | Descripción |
|---|---|---|
| E1 | `jiminy/turtlebot3_obstacle.yaml` | Validación de la cadena normativa básica de seguridad ante obstáculos. |
| E2 | `jiminy/turtlebot3_obstacle.yaml` con `distance_critical:=0.15` | Configurabilidad del umbral de parada en tiempo de ejecución, sin modificar ni recompilar el código. |
| E3 | `jiminy/turtlebot3_lidar_attacked_peer.yaml` | Evaluación del comportamiento cuando el LiDAR propio queda comprometido y se dispone de información procedente del peer. |
| E4 | Documentado en la memoria | Comparación entre la toma de decisiones aislada y distribuida en el sistema multi-robot. |
| E5 | `jiminy/turtlebot3_lidar_attacked_stop.yaml` y `src/lidar_jiminy_bridgeE5.py` | Parada forzada cuando ni el sensor propio ni el peer son fiables. |

Los experimentos multi-robot se ejecutaron sin SROS 2 activo para validar la capa de razonamiento basada en Jiminy. La validación de SROS 2 se realizó de forma independiente mediante análisis comparativo del tráfico DDS.

## Análisis de tráfico DDS

Durante el trabajo se realizaron capturas de tráfico de red con `tshark` y Wireshark para comparar el comportamiento del sistema con y sin SROS 2 habilitado.

Las capturas originales no se incluyen en este repositorio porque contienen información de red del entorno experimental, como direcciones IP y otros metadatos potencialmente sensibles. En su lugar, la memoria recoge los resultados agregados del análisis, incluyendo el número de paquetes RTPS y bytes observados en cada escenario.

Los comandos utilizados para la captura fueron:

```bash
sudo tshark -i <interfaz_wifi> -w baseline_sin_sros2.pcap
sudo tshark -i <interfaz_wifi> -w sros2_habilitado.pcap
```

El filtrado del tráfico RTPS se realizó posteriormente con:

```bash
tshark -r baseline_sin_sros2.pcap -Y rtps
tshark -r sros2_habilitado.pcap -Y rtps
```

En una versión futura del repositorio podrían incorporarse capturas filtradas o anonimizadas, siempre que no expongan información sensible del entorno de red.

## Consideraciones de seguridad

Por motivos de seguridad, no deben subirse al repositorio:

- claves privadas;
- keystores completos de SROS 2;
- certificados sensibles;
- tokens;
- credenciales;
- capturas `.pcap` o `.pcapng` con tráfico personal o no anonimizado;
- direcciones IP o MAC que no se deseen publicar;
- archivos temporales de compilación.

En caso de incluir material relacionado con SROS 2, se recomienda publicar únicamente políticas, plantillas o ejemplos sin secretos.

## Relación con la memoria

Este repositorio complementa la memoria del TFM proporcionando trazabilidad técnica del trabajo realizado. La memoria describe el diseño, la metodología, los resultados experimentales y las limitaciones del enfoque propuesto, mientras que este repositorio recoge parte del material práctico empleado durante la implementación y validación.

## Autor

Diego Pastrana Crespo

Máster Universitario en Investigación en Ciberseguridad