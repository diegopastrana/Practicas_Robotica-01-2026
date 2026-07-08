#!/usr/bin/env python3
# MIT License
#
# TFM: Análisis de la toma de decisiones y la ciberseguridad en sistemas
#      multi-robot distribuidos basados en ROS2
# Universidad de León — Máster en Investigación en Ciberseguridad
#
# lidar_jiminy_bridge.py
# Nodo puente entre el LiDAR del TurtleBot3 y el motor de decisión Jiminy.
# v5 — Lógica de casos revisada:
#   Caso A (lidar_attacked=False): el robot decide SOLO con su propio LiDAR.
#   Caso B (lidar_attacked=True, peer_trusted=True): usa datos del peer vía TF.
#   Caso C (lidar_attacked=True, peer_trusted=False): para por precaución.

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from jiminy_msgs.srv import CallJiminy
from jiminy_msgs.msg import Semantics

from tf2_ros import Buffer, TransformListener, LookupException, ConnectivityException, ExtrapolationException

# Velocidades
SPEED_SLOW = 0.02
SPEED_STOP = 0.0


class LidarJiminyBridge(Node):

    def __init__(self):
        super().__init__('lidar_jiminy_bridge')

        # Parámetros configurables
        self.declare_parameter('namespace', '')
        self.declare_parameter('peer_namespace', '')
        self.declare_parameter('peer_trusted', True)
        self.declare_parameter('lidar_attacked', False)
        self.declare_parameter('distance_critical', 0.30)
        self.declare_parameter('distance_caution', 0.60)
        # Umbral de relevancia espacial del peer.
        # Si la distancia entre robots (en el frame 'world') supera este valor,
        # el obstáculo del peer NO se introduce como w6 aunque exista.
        self.declare_parameter('peer_relevance_distance', 1.5)

        ns  = self.get_parameter('namespace').get_parameter_value().string_value
        peer_ns = self.get_parameter('peer_namespace').get_parameter_value().string_value
        self.peer_trusted           = self.get_parameter('peer_trusted').get_parameter_value().bool_value
        self.lidar_attacked         = self.get_parameter('lidar_attacked').get_parameter_value().bool_value
        self.distance_critical      = self.get_parameter('distance_critical').get_parameter_value().double_value
        self.distance_caution       = self.get_parameter('distance_caution').get_parameter_value().double_value
        self.peer_relevance_distance = self.get_parameter('peer_relevance_distance').get_parameter_value().double_value

        # Frames TF de cada robot (base_footprint en el frame world)
        self.own_frame  = f'{ns}/base_footprint'  if ns      else 'base_footprint'
        self.peer_frame = f'{peer_ns}/base_footprint' if peer_ns else None

        # TF2 — solo se inicializa si hay peer_namespace definido (Casos B y C).
        # En Caso A no se necesita TF y evitamos interferencias con el spin.
        self.tf_buffer   = None
        self.tf_listener = None
        if peer_ns:
            self.tf_buffer   = Buffer()
            self.tf_listener = TransformListener(self.tf_buffer, self)

        # Topics
        scan_topic          = f'/{ns}/scan'           if ns      else '/scan'
        peer_decision_topic = f'/{peer_ns}/jiminy_decision' if peer_ns else None
        decision_topic      = f'/{ns}/jiminy_decision' if ns      else '/jiminy_decision'
        cmd_vel_topic       = f'/{ns}/cmd_vel'         if ns      else '/cmd_vel'
        teleop_topic        = f'/{ns}/cmd_vel_teleop'  if ns      else '/cmd_vel_teleop'

        # QoS compatible con el LiDAR
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        self.scan_sub    = self.create_subscription(LaserScan, scan_topic, self.scan_callback, qos)
        self.teleop_cmd  = Twist()
        self.teleop_sub  = self.create_subscription(Twist, teleop_topic, self.teleop_callback, 10)

        self.peer_obstacle = False
        self.peer_critical = False
        if peer_decision_topic:
            self.peer_sub = self.create_subscription(
                String, peer_decision_topic, self.peer_callback, 10)
            self.get_logger().info(f'Listening to peer decisions on {peer_decision_topic}')

        jiminy_service = f'/{ns}/call_jiminy' if ns else '/call_jiminy'

        self.decision_pub  = self.create_publisher(String, decision_topic, 10)
        self.cmd_vel_pub   = self.create_publisher(Twist,  cmd_vel_topic,  10)
        self.jiminy_client = self.create_client(CallJiminy, jiminy_service)

        self.last_decision  = ''
        self.current_action = 'd_move'
        self._jiminy_call_in_progress = False

        # Heartbeat: republica la última decisión conocida cada 2s aunque
        # no haya cambiado. Esto evita que un peer se quede "mudo" en
        # jiminy_decision si su LiDAR se queda atascado en la misma lectura
        # (p.ej. por un fallo de cable) — el peer sigue emitiendo señal de
        # vida con el último estado real conocido.
        self._last_decision_msg = None
        self.create_timer(2.0, self._heartbeat_timer)

        self.get_logger().info('LidarJiminyBridge v5 started.')
        self.get_logger().info(f'LiDAR topic:              {scan_topic}')
        self.get_logger().info(f'Teleop topic:             {teleop_topic}')
        self.get_logger().info(f'CMD_VEL topic:            {cmd_vel_topic}')
        self.get_logger().info(f'Decision topic:           {decision_topic}')
        self.get_logger().info(f'Jiminy service:           {jiminy_service}')
        self.get_logger().info(f'Own TF frame:             {self.own_frame}')
        self.get_logger().info(f'Peer TF frame:            {self.peer_frame}')
        self.get_logger().info(f'Peer trusted:             {self.peer_trusted}')
        self.get_logger().info(f'LiDAR attacked:           {self.lidar_attacked}')
        self.get_logger().info(f'Distance critical:        {self.distance_critical} m')
        self.get_logger().info(f'Distance caution:         {self.distance_caution} m')
        self.get_logger().info(f'Peer relevance distance:  {self.peer_relevance_distance} m')

    # ------------------------------------------------------------------
    # TF helper — distancia euclidea entre robots en el frame 'world'
    # Devuelve float (metros) o None si no hay transform disponible.
    # ------------------------------------------------------------------
    def _peer_distance(self) -> float | None:
        if self.peer_frame is None or self.tf_buffer is None:
            return None
        try:
            # Transformación del frame del peer en el frame propio.
            # timeout=1.0s permite que el buffer TF reciba los frames
            # dinámicos del peer antes de fallar.
            t = self.tf_buffer.lookup_transform(
                self.own_frame,     # frame destino (robot local)
                self.peer_frame,    # frame origen  (robot peer)
                rclpy.time.Time(),  # tiempo más reciente disponible
                timeout=rclpy.duration.Duration(seconds=0.1)
            )
            tx = t.transform.translation.x
            ty = t.transform.translation.y
            return math.sqrt(tx * tx + ty * ty)
        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            self.get_logger().warn(
                f'TF lookup failed ({self.peer_frame} → {self.own_frame}): {e}',
                throttle_duration_sec=5.0
            )
            return None

    # ------------------------------------------------------------------
    # Decide si el peer es espacialmente relevante.
    # Si no hay TF disponible, se considera relevante por precaución.
    # ------------------------------------------------------------------
    def _peer_is_spatially_relevant(self) -> bool:
        dist = self._peer_distance()
        if dist is None:
            # Sin TF, asumimos relevante (comportamiento conservador)
            self.get_logger().warn(
                'TF unavailable — assuming peer is spatially relevant.',
                throttle_duration_sec=5.0
            )
            return True
        relevant = dist <= self.peer_relevance_distance
        self.get_logger().debug(
            f'Peer distance: {dist:.2f} m | relevance threshold: '
            f'{self.peer_relevance_distance} m | relevant: {relevant}'
        )
        return relevant

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _heartbeat_timer(self):
        """Republica la última decisión conocida cada 2s, aunque no haya
        cambiado, para que los peers no dejen de recibir señal de vida si
        el LiDAR propio se queda atascado en la misma lectura."""
        if self._last_decision_msg is None:
            return
        msg = String()
        msg.data = self._last_decision_msg
        self.decision_pub.publish(msg)

    def teleop_callback(self, msg: Twist):
        self.teleop_cmd = msg
        if self.current_action == 'd_stop':
            self.cmd_vel_pub.publish(Twist())
        elif self.current_action == 'd_slow_down':
            limited = Twist()
            # Limita la MAGNITUD del avance lineal preservando el sentido
            # (adelante o atrás), sin restringir el giro.
            if msg.linear.x > 0:
                limited.linear.x = min(msg.linear.x, SPEED_SLOW)
            elif msg.linear.x < 0:
                limited.linear.x = max(msg.linear.x, -SPEED_SLOW)
            else:
                limited.linear.x = 0.0
            limited.angular.z = msg.angular.z
            self.cmd_vel_pub.publish(limited)
        else:
            self.cmd_vel_pub.publish(msg)

    def peer_callback(self, msg: String):
        # Extrae la acción real del peer del inicio exacto del mensaje
        # (evita falsos positivos de "in" sobre substrings).
        peer_action = msg.data.split('|')[0].strip()
        self.peer_obstacle = peer_action in ('d_stop', 'd_slow_down')
        self.peer_critical = (peer_action == 'd_stop')
        self.get_logger().info(
            f'Peer data received: "{msg.data}" '
            f'(peer_action={peer_action}, peer_critical={self.peer_critical})',
            throttle_duration_sec=2.0
        )

        if not self.lidar_attacked:
            return

        # DECISIÓN DIRECTA Y DETERMINISTA:
        # el movimiento del robot se controla aquí mismo, sin depender de
        # la respuesta asíncrona de Jiminy (que puede llegar desordenada
        # bajo llamadas concurrentes). Se aplica el filtro de relevancia
        # espacial por TF antes de decidir.
        peer_relevant = self._peer_is_spatially_relevant()

        if peer_relevant and self.peer_critical:
            new_action = 'd_stop'
            fact_used = 'w6b'
        elif peer_relevant and self.peer_obstacle:
            new_action = 'd_slow_down'
            fact_used = 'w6'
        else:
            new_action = 'd_move'
            fact_used = 'w5'

        self.current_action = new_action

        cmd = Twist()
        if new_action == 'd_stop':
            pass  # Twist() vacío -> parada total
        elif new_action == 'd_slow_down':
            last_x = self.teleop_cmd.linear.x
            if last_x > 0:
                cmd.linear.x = min(last_x, SPEED_SLOW)
            elif last_x < 0:
                cmd.linear.x = max(last_x, -SPEED_SLOW)
            cmd.angular.z = self.teleop_cmd.angular.z
        else:  # d_move
            cmd = self.teleop_cmd
        self.cmd_vel_pub.publish(cmd)

        self.get_logger().info(
            f'[REACTIVE] Decision: {new_action} | fact={fact_used} | '
            f'peer_relevant={peer_relevant}'
        )

        # Llamada a Jiminy en paralelo, únicamente para dejar constancia
        # oficial en el topic jiminy_decision (auditoría/memoria). Su
        # respuesta NO debe alterar current_action ni el movimiento —
        # eso ya se ha resuelto arriba de forma determinista.
        if self._jiminy_call_in_progress:
            return
        if not self.jiminy_client.service_is_ready():
            return
        facts = ['w4', 'w9', fact_used, 'w7' if self.peer_trusted else 'w8']
        self._jiminy_call_in_progress = True
        self.call_jiminy(facts, -1.0)

    def scan_callback(self, msg: LaserScan):
        # ---- Modo LiDAR atacado ----
        if self.lidar_attacked:
            self.get_logger().warn(
                'LiDAR attacked: ignoring own sensor data.',
                throttle_duration_sec=5.0
            )
            # En este modo, la decisión se dispara exclusivamente desde
            # peer_callback (única fuente de información válida). Llamar
            # a Jiminy también aquí duplicaría peticiones concurrentes al
            # mismo servicio y aumentaría la latencia percibida.
            return

        # ---- Caso A: LiDAR propio funciona correctamente ----
        # El robot decide SOLO en base a su propio LiDAR.
        # La información del peer se sigue recibiendo (peer_callback activo)
        # pero no se introduce en los hechos — el LiDAR propio es prioritario.
        # La activación del peer queda como trabajo futuro (detección automática
        # de anomalías en el LiDAR); aquí se simula con lidar_attacked:=true.
        valid_ranges = [r for r in msg.ranges if msg.range_min < r < msg.range_max]
        if not valid_ranges:
            self.get_logger().warn('No valid LiDAR readings, skipping.')
            return

        min_distance = min(valid_ranges)
        facts = []

        if min_distance < self.distance_critical:
            facts.append('w1')
        elif min_distance < self.distance_caution:
            facts.append('w2')
        else:
            facts.append('w3')

        facts.append('w4')

        if hasattr(self, 'peer_sub'):
            self.get_logger().info(
                f'Peer data available (peer reports obstacle={self.peer_obstacle}) '
                f'but IGNORED — own LiDAR operational, deciding independently (Case A).',
                throttle_duration_sec=3.0
            )

        if not self.jiminy_client.wait_for_service(timeout_sec=0.5):
            self.get_logger().warn('Jiminy service not available, skipping.')
            return

        self.call_jiminy(facts, min_distance)

    # ------------------------------------------------------------------
    def call_jiminy(self, facts: list, min_distance: float):
        request = CallJiminy.Request()
        request.semantics = Semantics()
        request.semantics.semantics = 'priority'
        request.facts = facts
        future = self.jiminy_client.call_async(request)
        future.add_done_callback(
            lambda f: self.jiminy_response_callback(f, facts, min_distance)
        )

    def jiminy_response_callback(self, future, facts: list, min_distance: float):
        self._jiminy_call_in_progress = False
        try:
            response = future.result()
        except Exception as e:
            self.get_logger().error(f'Jiminy service call failed: {e}')
            return

        if not response.success:
            self.get_logger().error(f'Jiminy error: {response.message}')
            return

        conclusions = [norm.conclusion for norm in response.accepted]

        if 'd_stop' in conclusions:
            action = 'd_stop'
        elif 'd_slow_down' in conclusions:
            action = 'd_slow_down'
        elif 'd_move' in conclusions:
            action = 'd_move'
        else:
            action = 'd_prefer_safe'

        # En modo lidar_attacked, current_action y cmd_vel ya se controlan
        # de forma determinista en peer_callback. Aquí solo publicamos el
        # log/topic de decisión oficial para auditoría — sin tocar
        # current_action ni cmd_vel, evitando cualquier sobrescritura por
        # respuestas asíncronas desordenadas.
        if self.lidar_attacked:
            if action != self.last_decision:
                self.last_decision = action
                msg      = String()
                dist_str = 'N/A'
                msg.data = (
                    f'{action} | dist={dist_str} | facts={facts} | accepted={conclusions}'
                )
                self.decision_pub.publish(msg)
                self._last_decision_msg = msg.data
                self.get_logger().info(
                    f'Decision (log-only): {action} | facts={facts}'
                )
            return

        self.current_action = action

        if action != self.last_decision:
            self.last_decision = action
            msg      = String()
            dist_str = f'{min_distance:.3f}m' if min_distance >= 0 else 'N/A'
            msg.data = (
                f'{action} | dist={dist_str} | facts={facts} | accepted={conclusions}'
            )
            self.decision_pub.publish(msg)
            self._last_decision_msg = msg.data
            self.get_logger().info(
                f'Decision: {action} | dist={dist_str} | facts={facts}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = LidarJiminyBridge()
    # SingleThreadedExecutor: procesa los callbacks uno a uno, sin
    # solapamientos. Esto elimina las condiciones de carrera entre
    # teleop_callback, peer_callback y el timer de heartbeat que se
    # daban con MultiThreadedExecutor (p.ej. republicar un cmd_vel
    # obsoleto justo después de una parada). El timeout corto de TF
    # (0.1s) evita que un lookup lento bloquee el resto de callbacks.
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
