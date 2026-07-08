# Análisis de la toma de decisiones y la ciberseguridad en sistemas multi-robot distribuidos basados en ROS 2

Repositorio asociado al Trabajo de Fin de Máster del Máster Universitario en Investigación en Ciberseguridad.

El proyecto estudia la seguridad y la resiliencia de un sistema multi-robot basado en ROS 2 Humble, utilizando dos TurtleBot3 Burger reales. El trabajo combina dos capas complementarias:

- **SROS 2 / DDS-Security**, para proteger las comunicaciones DDS mediante autenticación y cifrado.
- **Jiminy**, como framework normativo deóntico para razonar sobre la fiabilidad de la información recibida y tomar decisiones conservadoras ante datos no fiables.

La integración automática entre ambas capas no forma parte de la implementación final. En el prototipo desarrollado, el estado de confianza del peer se modela mediante un parámetro, quedando su derivación automática desde el estado real de DDS-Security como trabajo futuro.

## Objetivo del repositorio

Este repositorio recoge el material técnico desarrollado durante el TFM:

- nodos ROS 2 implementados;
- escenarios y reglas normativas utilizadas con Jiminy;
- ficheros de configuración de los experimentos;
- configuraciones relacionadas con SROS 2;
- scripts auxiliares de ejecución y análisis;
- documentación complementaria del entorno experimental.

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

## Estructura prevista del repositorio

```text
.
├── README.md
├── src/
│   └── lidar_jiminy_bridge.py
├── config/
│   ├── parameters_e1.yaml
│   ├── parameters_e2.yaml
│   ├── parameters_e3.yaml
│   ├── parameters_e4.yaml
│   └── parameters_e5.yaml
├── jiminy/
│   ├── e1_basic_safety.yaml
│   ├── e2_stop_threshold.yaml
│   ├── e3_peer_trusted.yaml
│   ├── e4_distributed_decision.yaml
│   └── e5_peer_untrusted.yaml
├── sros2/
│   ├── policies/
│   │   ├── governance.xml
│   │   └── permissions.xml
│   └── README.md
├── scripts/
│   ├── run_e1.sh
│   ├── run_e2.sh
│   ├── run_e3.sh
│   ├── run_e4.sh
│   ├── run_e5.sh
│   └── analyze_rtps.sh
└── docs/
    └── figuras/
```

La estructura anterior resume la organización del material técnico asociado al TFM. Los nombres concretos de los ficheros pueden variar respecto al entorno local original, pero se mantiene la separación entre código, configuración, escenarios normativos, scripts y documentación auxiliar.

## Nodo principal

El nodo principal desarrollado es:

```text
src/lidar_jiminy_bridge.py
```

Este nodo actúa como puente entre la información sensorial de ROS 2 y el modelo normativo de Jiminy. Su función es transformar el estado observado del entorno y del peer en hechos normativos que permiten determinar la acción del robot.

Entre los hechos considerados se incluyen:

- presencia o ausencia de obstáculo;
- fiabilidad del LiDAR propio;
- estado de confianza del peer;
- disponibilidad de información remota;
- decisión de avanzar o detenerse.

## Casos de prueba

La validación experimental se estructuró en cinco casos de prueba:

| Caso | Descripción |
|---|---|
| E1 | Validación de la cadena normativa básica de seguridad ante obstáculos. |
| E2 | Configurabilidad del umbral de parada. |
| E3 | Autonomía con sensor propio fiable. |
| E4 | Recuperación de capacidad de decisión mediante un peer fiable cuando el LiDAR propio queda comprometido. |
| E5 | Parada forzada cuando ni el sensor propio ni el peer son fiables. |

Los experimentos E3, E4 y E5 se ejecutaron en un escenario multi-robot. La validación de Jiminy se realizó sin SROS 2 activo, mientras que la validación de SROS 2 se realizó mediante análisis comparativo del tráfico DDS.

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

Este repositorio complementa la memoria del TFM proporcionando trazabilidad técnica del trabajo realizado. La memoria describe el diseño, la metodología, los resultados experimentales y las limitaciones del enfoque propuesto, mientras que este repositorio recoge el material práctico empleado durante la implementación y validación.

## Autor

Diego Pastrana Crespo

Máster Universitario en Investigación en Ciberseguridad
