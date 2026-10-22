#!/usr/bin/env python3
#
# Green Traffic Light Publisher Node
# Publishes all traffic lights as GREEN at 100Hz for testing/simulation
#

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSHistoryPolicy
from rclpy.executors import MultiThreadedExecutor
from autoware_perception_msgs.msg import (
    TrafficLightGroupArray,
    TrafficLightGroup,
    TrafficLightElement,
)
import os
import subprocess
import xml.etree.ElementTree as ET
import re


class GreenTrafficLightPublisher(Node):
    def __init__(self):
        super().__init__("green_traffic_light_publisher")
        self.get_logger().info("Initializing Green Traffic Light Publisher...")

        # Declare parameters
        self.declare_parameter("publish_rate", 100)  # Hz
        self.declare_parameter("auto_discover_ids", True)
        self.declare_parameter("lanelet2_map_path", "")
        self.declare_parameter("map_path", "")
        self.declare_parameter("lanelet_map_path", "")
        self.declare_parameter("vector_map_path", "")
        self.declare_parameter("discovery_retry_sec", 1.0)
        self.declare_parameter("discovery_timeout_sec", 1.0)
        self.declare_parameter(
            "traffic_light_ids",
            [],
        )

        # Get parameters
        publish_rate = self.get_parameter("publish_rate").value
        self.auto_discover_ids = self.get_parameter("auto_discover_ids").value
        self.discovery_retry_sec = float(self.get_parameter("discovery_retry_sec").value)
        self.discovery_timeout_sec = float(self.get_parameter("discovery_timeout_sec").value)
        self.traffic_light_ids = self._resolve_traffic_light_ids(fast_start=True)

        # Create publisher
        qos_profile = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self.get_logger().info(f"Creating publisher to /perception/traffic_light_recognition/traffic_signals")
        self.publisher = self.create_publisher(
            TrafficLightGroupArray,
            "/perception/traffic_light_recognition/traffic_signals",
            qos_profile,
        )
        self.get_logger().info("Publisher created successfully")

        self.discovery_timer = None
        if not self.traffic_light_ids and self.auto_discover_ids:
            self.discovery_timer = self.create_timer(
                max(self.discovery_retry_sec, 1.0), self._retry_discovery_callback
            )
            self.get_logger().warn(
                "No traffic light IDs found yet. Auto-discovery retry timer is active."
            )

        # Create timer for publishing
        period = 1.0 / publish_rate  # Convert Hz to seconds
        self.timer = self.create_timer(period, self.timer_callback)
        self.get_logger().info(f"Timer created with period {period} seconds")

        self.get_logger().info(
            f"Green Traffic Light Publisher started at {publish_rate}Hz"
        )
        self.get_logger().info(f"Traffic Light IDs: {self.traffic_light_ids}")

    def _retry_discovery_callback(self):
        if self.traffic_light_ids:
            if self.discovery_timer is not None:
                self.discovery_timer.cancel()
                self.discovery_timer = None
            return

        discovered_ids = self._discover_ids_from_map()
        if discovered_ids:
            self.traffic_light_ids = discovered_ids
            self.get_logger().info(
                f"Auto-discovery succeeded with {len(discovered_ids)} traffic light IDs"
            )
            self.get_logger().info(f"Traffic Light IDs: {self.traffic_light_ids}")
            if self.discovery_timer is not None:
                self.discovery_timer.cancel()
                self.discovery_timer = None

    def _resolve_traffic_light_ids(self, fast_start=False):
        manual_ids = self._normalize_int_list(self.get_parameter("traffic_light_ids").value)
        env_ids_raw = os.environ.get("TRAFFIC_LIGHT_IDS", "").strip()
        env_ids = []
        if env_ids_raw:
            env_ids = self._normalize_int_list(re.split(r"[,\s]+", env_ids_raw))
        if env_ids:
            manual_ids = sorted(set(manual_ids).union(env_ids))

        if not self.auto_discover_ids:
            if not manual_ids:
                self.get_logger().warn(
                    "auto_discover_ids is false and no traffic_light_ids were provided. "
                    "Set traffic_light_ids or TRAFFIC_LIGHT_IDS, or provide LANELET2_MAP_PATH."
                )
            return manual_ids

        discovered_ids = self._discover_ids_from_map(fast_start=fast_start)
        if discovered_ids:
            if manual_ids:
                merged = sorted(set(discovered_ids).union(manual_ids))
                self.get_logger().info(
                    "Using auto-discovered IDs merged with traffic_light_ids parameter"
                )
                return merged
            return discovered_ids

        if manual_ids:
            self.get_logger().warn(
                "Auto-discovery failed. Falling back to traffic_light_ids parameter and/or TRAFFIC_LIGHT_IDS."
            )
            return manual_ids

        self.get_logger().warn(
            "Auto-discovery failed and no manual traffic light IDs were provided. "
            "Set LANELET2_MAP_PATH or TRAFFIC_LIGHT_IDS."
        )
        return []

    def _discover_ids_from_map(self, fast_start=False):
        map_path = self._resolve_lanelet2_map_path(fast_start=fast_start)
        if not map_path:
            return []

        ids = self._extract_traffic_light_ids_from_osm(map_path)
        if ids:
            self.get_logger().info(
                f"Discovered {len(ids)} traffic light IDs from map: {map_path}"
            )
        else:
            self.get_logger().warn(
                f"No traffic light IDs found in map file: {map_path}"
            )
        return ids

    def _resolve_lanelet2_map_path(self, fast_start=False):
        param_path = str(self.get_parameter("lanelet2_map_path").value).strip()
        if param_path:
            resolved = self._resolve_map_path_candidate(param_path)
            if resolved:
                return resolved
            self.get_logger().warn(f"lanelet2_map_path does not exist: {os.path.expanduser(param_path)}")

        ros_discovered = self._discover_map_path_from_ros_params(fast_start=fast_start)
        if ros_discovered:
            return ros_discovered

        env_candidates = [
            os.environ.get("LANELET2_MAP_PATH", ""),
            os.environ.get("MAP_PATH", ""),
            os.environ.get("VECTOR_MAP_PATH", ""),
        ]
        for candidate in env_candidates:
            candidate = candidate.strip()
            if not candidate:
                continue
            resolved = self._resolve_map_path_candidate(candidate)
            if resolved:
                return resolved

        if fast_start:
            return ""

        return ""

    def _resolve_map_path_candidate(self, candidate_path):
        expanded = os.path.expanduser(candidate_path)
        if os.path.isfile(expanded):
            return expanded

        if not os.path.isdir(expanded):
            return ""

        preferred_names = ("lanelet2_map.osm",)
        for root, _, files in os.walk(expanded):
            for preferred_name in preferred_names:
                if preferred_name in files:
                    return os.path.join(root, preferred_name)

        return ""

    def _discover_map_path_from_ros_params(self, fast_start=False):
        prioritized_nodes = ["/map/lanelet2_map_loader"]
        for node_name in prioritized_nodes:
            value = self._ros2_param_get_string(node_name, "lanelet2_map_path")
            if not value:
                continue
            expanded = os.path.expanduser(value)
            if os.path.isfile(expanded):
                self.get_logger().info(
                    f"Found lanelet2 map path from ROS param: {node_name}.lanelet2_map_path"
                )
                return expanded

        if fast_start:
            return ""

        param_names = [
            "lanelet2_map_path",
            "map_path",
            "lanelet_map_path",
            "vector_map_path",
        ]

        nodes = self._ros2_node_list()
        for node_name in nodes:
            for param_name in param_names:
                value = self._ros2_param_get_string(node_name, param_name)
                if not value:
                    continue
                expanded = os.path.expanduser(value)
                if os.path.isfile(expanded):
                    self.get_logger().info(
                        f"Found lanelet2 map path from ROS param: {node_name}.{param_name}"
                    )
                    return expanded

        return ""

    def _ros2_node_list(self):
        completed = self._run_command(["ros2", "node", "list"])
        if not completed or completed.returncode != 0:
            return []

        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        return lines

    def _ros2_param_get_string(self, node_name, param_name):
        completed = self._run_command(["ros2", "param", "get", node_name, param_name])
        if not completed or completed.returncode != 0:
            return ""

        marker = "String value is:"
        output = completed.stdout.strip()
        if marker not in output:
            return ""

        value = output.split(marker, maxsplit=1)[1].strip()
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        return value.strip()

    def _run_command(self, command):
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=max(self.discovery_timeout_sec, 1.0),
                check=False,
            )
        except (subprocess.SubprocessError, OSError):
            return None

    def _extract_traffic_light_ids_from_osm(self, osm_path):
        try:
            root = ET.parse(osm_path).getroot()
        except (ET.ParseError, OSError) as error:
            self.get_logger().error(f"Failed to parse OSM map: {error}")
            return []

        relation_ids = set()
        for relation in root.findall("relation"):
            tags = {
                tag.attrib.get("k", ""): tag.attrib.get("v", "")
                for tag in relation.findall("tag")
            }
            if tags.get("type") == "regulatory_element" and tags.get("subtype") == "traffic_light":
                relation_id = relation.attrib.get("id")
                if relation_id is None:
                    continue
                try:
                    relation_ids.add(int(relation_id))
                except ValueError:
                    continue

        if relation_ids:
            return sorted(relation_ids)

        # Fallback for non-standard maps: use way IDs tagged as traffic_light.
        way_ids = set()
        for way in root.findall("way"):
            tags = {
                tag.attrib.get("k", ""): tag.attrib.get("v", "")
                for tag in way.findall("tag")
            }
            if tags.get("type") == "traffic_light":
                way_id = way.attrib.get("id")
                if way_id is None:
                    continue
                try:
                    way_ids.add(int(way_id))
                except ValueError:
                    continue

        if way_ids:
            self.get_logger().warn(
                "Using fallback traffic_light way IDs because no traffic_light regulatory relations were found."
            )
        return sorted(way_ids)

    @staticmethod
    def _normalize_int_list(values):
        result = []
        for value in values:
            try:
                result.append(int(value))
            except (TypeError, ValueError):
                continue
        return sorted(set(result))

    def timer_callback(self):
        try:
            if not self.traffic_light_ids:
                return

            # Create TrafficLightGroupArray message
            msg = TrafficLightGroupArray()

            # Set timestamp
            now = self.get_clock().now().to_msg()
            msg.stamp = now

            # Create a green traffic light element
            for traffic_light_id in self.traffic_light_ids:
                # Create traffic light element (GREEN, CIRCLE, SOLID_ON)
                element = TrafficLightElement()
                element.color = TrafficLightElement.GREEN
                element.shape = TrafficLightElement.CIRCLE
                element.status = TrafficLightElement.SOLID_ON
                element.confidence = 1.0

                # Create traffic light group
                group = TrafficLightGroup()
                group.traffic_light_group_id = traffic_light_id
                group.elements.append(element)

                # Add to array
                msg.traffic_light_groups.append(group)

            # Publish message
            self.publisher.publish(msg)
            self.get_logger().debug(f"Published {len(msg.traffic_light_groups)} green traffic lights")
        except Exception as e:
            self.get_logger().error(f"Error in timer_callback: {e}", exc_info=True)


def main(args=None):
    rclpy.init(args=args)
    node = GreenTrafficLightPublisher()

    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down...")
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
