#!/usr/bin/env python3
"""
brain_sim Test Suite
====================
Tests for simulation components: SDF validity, world integrity,
model completeness, configuration consistency, and SimBridge API.

Usage:
    python tests/test_simulation.py
    python tests/test_simulation.py --verbose
"""

import json
import os
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "brain_sim"))

# Test will run with or without the SimBridge module
try:
    from brain_sim.sim_bridge import SimBridge, SimConfig, Pose3D, SimObject, create_sim_config
    HAS_SIM_BRIDGE = True
except ImportError:
    HAS_SIM_BRIDGE = False
    print("[WARN] sim_bridge module not importable — API tests will be skipped")


# ============================================================================
# Test Fixtures & Helpers
# ============================================================================

class SimTestBase(unittest.TestCase):
    """Base class with utility methods for simulation tests."""
    
    @property
    def brain_sim_dir(self):
        return PROJECT_ROOT / "brain_sim"
    
    @property
    def gazebo_dir(self):
        return self.brain_sim_dir / "gazebo"
    
    def parse_xml(self, filepath: Path):
        """Parse XML/SDF file, return root element."""
        try:
            tree = ET.parse(str(filepath))
            return tree.getroot()
        except ET.ParseError as e:
            self.fail(f"XML parse error in {filepath.name}: {e}")


# ============================================================================
# Test 1: SDF Robot Model Validation
# ============================================================================

class TestRobotSDF(SimTestBase):
    """Validate robot SDF model files."""
    
    def test_kinova_gen3_sdf_exists(self):
        """Kinova Gen3 SDF file exists and is non-empty."""
        path = self.gazebo_dir / "robots" / "kinova_gen3.sdf"
        self.assertTrue(path.exists(), f"Missing: {path}")
        content = path.read_text(encoding="utf-8")
        self.assertGreater(len(content), 100, "Kinova Gen3 SDF is too small (<100 bytes)")
    
    def test_kinova_gen3_xml_valid(self):
        """Kinova Gen3 SDF is valid XML."""
        root = self.parse_xml(self.gazebo_dir / "robots" / "kinova_gen3.sdf")
        self.assertEqual(root.tag, "sdf", "Root tag should be <sdf>")
    
    def test_kinova_gen3_has_model(self):
        """Kinova Gen3 SDF contains a <model> element."""
        root = self.parse_xml(self.gazebo_dir / "robots" / "kinova_gen3.sdf")
        model = root.find("model")
        self.assertIsNotNone(model, "Missing <model> element")
        self.assertEqual(model.get("name"), "kinova_gen3")
    
    def test_kinova_gen3_arm_joints(self):
        """Kinova Gen3 has 7 arm joints (joint_1 through joint_7)."""
        root = self.parse_xml(self.gazebo_dir / "robots" / "kinova_gen3.sdf")
        # Use ".//model/joint" to only find structural joints (not plugin <joint> children)
        joints = root.findall(".//model/joint")
        joint_names = [j.get("name") for j in joints if j.get("name")]
        
        # Expected arm joints
        expected_joints = [f"joint_{i}" for i in range(1, 8)]
        for ej in expected_joints:
            self.assertIn(ej, joint_names, f"Missing arm joint: {ej}")
        
        # All joints should be revolute
        for j in joints:
            if j.get("name", "").startswith("joint_"):
                self.assertEqual(j.get("type"), "revolute",
                                 f"Arm joint {j.get('name')} should be revolute")
    
    def test_kinova_gen3_gripper_joints(self):
        """Kinova Gen3 has 2 prismatic gripper joints."""
        root = self.parse_xml(self.gazebo_dir / "robots" / "kinova_gen3.sdf")
        joints = root.findall(".//model/joint")
        joint_names = [j.get("name") for j in joints if j.get("name")]
        
        self.assertIn("finger_left_joint", joint_names, "Missing left finger joint")
        self.assertIn("finger_right_joint", joint_names, "Missing right finger joint")
        
        for j in joints:
            if "finger" in (j.get("name") or ""):
                self.assertEqual(j.get("type"), "prismatic",
                                 f"Finger joint {j.get('name')} should be prismatic")
    
    def test_kinova_gen3_total_joints(self):
        """Kinova Gen3 has exactly 10 joints (7 arm + 1 base + 2 finger)."""
        root = self.parse_xml(self.gazebo_dir / "robots" / "kinova_gen3.sdf")
        joints = root.findall(".//model/joint")
        # Expected: joint_1-7 (revolute) + gripper_base_joint (fixed)
        #           + finger_left_joint (prismatic) + finger_right_joint (prismatic) = 10
        self.assertEqual(len(joints), 10,
                         f"Expected 10 joints, got {len(joints)}")
    
    def test_kinova_gen3_has_gazebo_plugins(self):
        """Kinova Gen3 has Gazebo sensor/controller plugins."""
        root = self.parse_xml(self.gazebo_dir / "robots" / "kinova_gen3.sdf")
        plugins = root.findall(".//plugin")
        plugin_names = [p.get("name", "") for p in plugins]
        
        # Expected plugins
        expected = [
            "joint_state_publisher",
            "arm_controller",
            "gripper_controller",
        ]
        for ep in expected:
            found = any(ep in pn for pn in plugin_names)
            self.assertTrue(found, f"Missing plugin: {ep}")
    
    def test_kinova_gen3_collision_geometries(self):
        """Each link has collision geometry."""
        root = self.parse_xml(self.gazebo_dir / "robots" / "kinova_gen3.sdf")
        links = root.findall(".//link")
        for link in links:
            link_name = link.get("name", "unknown")
            collision = link.find("collision")
            self.assertIsNotNone(collision,
                                 f"Link '{link_name}' missing collision geometry")
    
    def test_kinova_gen3_inertial(self):
        """Arm links have inertial properties."""
        root = self.parse_xml(self.gazebo_dir / "robots" / "kinova_gen3.sdf")
        links = root.findall(".//link")
        arm_links = [l for l in links 
                     if l.get("name", "") and "finger" not in l.get("name", "")
                     and "gripper" not in l.get("name", "")]
        
        for link in arm_links:
            link_name = link.get("name")
            inertial = link.find("inertial")
            self.assertIsNotNone(inertial,
                                 f"Link '{link_name}' missing <inertial>")
            mass = inertial.find("mass")
            self.assertIsNotNone(mass,
                                 f"Link '{link_name}' missing <mass>")
            inertia_matrix = inertial.find("inertia")
            self.assertIsNotNone(inertia_matrix,
                                 f"Link '{link_name}' missing <inertia>")
    
    def test_turtlebot4_sdf_exists(self):
        """TurtleBot 4 SDF file exists and is non-empty."""
        path = self.gazebo_dir / "robots" / "turtlebot4.sdf"
        self.assertTrue(path.exists(), f"Missing: {path}")
        content = path.read_text(encoding="utf-8")
        self.assertGreater(len(content), 100, "TurtleBot 4 SDF is too small")
    
    def test_turtlebot4_has_diff_drive(self):
        """TurtleBot 4 has differential drive controller plugin."""
        path = self.gazebo_dir / "robots" / "turtlebot4.sdf"
        content = path.read_text(encoding="utf-8")
        self.assertIn("diff_drive", content.lower(),
                      "TurtleBot 4 missing differential drive plugin")
    
    def test_turtlebot4_has_sensors(self):
        """TurtleBot 4 has camera, lidar, and IMU sensors."""
        path = self.gazebo_dir / "robots" / "turtlebot4.sdf"
        content = path.read_text(encoding="utf-8")
        self.assertIn("rplidar", content.lower(), "TurtleBot 4 missing lidar")
        self.assertIn("oakd", content.lower(), "TurtleBot 4 missing OAK-D camera")
        self.assertIn("bmi160", content.lower(), "TurtleBot 4 missing IMU")
    
    def test_turtlebot4_4_wheels(self):
        """TurtleBot 4 has 4 wheels (2 drive + 2 caster)."""
        path = self.gazebo_dir / "robots" / "turtlebot4.sdf"
        content = path.read_text(encoding="utf-8")
        self.assertIn("left_wheel", content)
        self.assertIn("right_wheel", content)
        self.assertIn("front_caster", content)
        self.assertIn("rear_caster", content)


# ============================================================================
# Test 2: World File Validation
# ============================================================================

class TestWorldFiles(SimTestBase):
    """Validate Gazebo world files."""
    
    def _validate_world(self, world_name):
        """Helper: validate a .world file."""
        path = self.gazebo_dir / "worlds" / f"{world_name}.world"
        self.assertTrue(path.exists(), f"Missing: {path}")
        
        content = path.read_text(encoding="utf-8")
        self.assertGreater(len(content), 100,
                          f"{world_name}.world is too small (<100 bytes)")
        
        # Parse XML
        root = self.parse_xml(path)
        self.assertEqual(root.tag, "sdf", f"{world_name}: root should be <sdf>")
        
        world = root.find("world")
        self.assertIsNotNone(world, f"{world_name}: missing <world> element")
        self.assertIsNotNone(world.get("name"), f"{world_name}: missing world name")
        
        # Must have physics
        physics = world.find("physics")
        self.assertIsNotNone(physics, f"{world_name}: missing <physics>")
        
        return root, world
    
    def test_tabletop_world_valid(self):
        """Tabletop world is valid XML and contains required elements."""
        root, world = self._validate_world("tabletop")
        
        # Expected models (inline or include)
        # Tabletop should have table and objects
        content = ET.tostring(root, encoding="unicode")
        self.assertIn("table", content.lower(), "Tabletop missing table model")
        self.assertIn("red_cup", content.lower(), "Tabletop missing red cup")
        self.assertIn("ground_plane", content.lower(), "Tabletop missing ground")
    
    def test_warehouse_world_valid(self):
        """Warehouse world is valid XML."""
        root, world = self._validate_world("warehouse")
        
        content = ET.tostring(root, encoding="unicode")
        # Warehouse has shelves, pallets, walls
        self.assertIn("shelf", content.lower(), "Warehouse missing shelves")
        self.assertIn("wall", content.lower(), "Warehouse missing walls")
        self.assertIn("ground_plane", content.lower(), "Warehouse missing ground")
    
    def test_living_room_world_valid(self):
        """Living room world is valid XML."""
        root, world = self._validate_world("living_room")
        
        content = ET.tostring(root, encoding="unicode")
        # Living room has sofa, coffee table, TV, bookshelf
        self.assertIn("sofa", content.lower(), "Living room missing sofa")
        self.assertIn("coffee", content.lower(), "Living room missing coffee table")
        self.assertIn("tv", content.lower(), "Living room missing TV")
        self.assertIn("bookshelf", content.lower(), "Living room missing bookshelf")
        
        # Should have both a Kinova arm and a TurtleBot base
        self.assertIn("kinova_gen3", content.lower(), "Living room missing Kinova arm")
        self.assertIn("turtlebot4", content.lower(), "Living room missing TurtleBot")
    
    def test_all_worlds_have_physics(self):
        """All worlds have physics configuration."""
        for world_name in ["tabletop", "warehouse", "living_room"]:
            with self.subTest(world=world_name):
                _, world = self._validate_world(world_name)
                physics = world.find("physics")
                # Check physics engine is specified
                self.assertTrue(
                    physics.get("type") in ("ode", "bullet", "dart", "simbody"),
                    f"{world_name}: invalid physics type"
                )
    
    def test_all_worlds_have_lighting(self):
        """All worlds have at least one light source."""
        for world_name in ["tabletop", "warehouse", "living_room"]:
            with self.subTest(world=world_name):
                _, world = self._validate_world(world_name)
                lights = world.findall("light")
                self.assertGreater(len(lights), 0,
                                   f"{world_name}: no light sources found")


# ============================================================================
# Test 3: Model Completeness
# ============================================================================

class TestModelCompleteness(SimTestBase):
    """Validate Gazebo model directories."""
    
    def _check_model(self, model_name, required_links=None):
        """Helper: validates a model directory has model.sdf + model.config."""
        model_dir = self.gazebo_dir / "models" / model_name
        self.assertTrue(model_dir.is_dir(), f"Model dir missing: {model_dir}")
        
        sdf_file = model_dir / "model.sdf"
        self.assertTrue(sdf_file.exists(), f"Missing: {sdf_file}")
        
        config_file = model_dir / "model.config"
        self.assertTrue(config_file.exists(), f"Missing: {config_file}")
        
        # Validate model.config structure
        config_root = self.parse_xml(config_file)
        self.assertEqual(config_root.tag, "model", 
                        f"{model_name} config: root should be <model>")
        
        # Validate model.sdf link count if specified
        if required_links is not None:
            sdf_root = self.parse_xml(sdf_file)
            links = sdf_root.findall(".//link")
            self.assertGreaterEqual(len(links), required_links,
                                    f"{model_name}: expected >= {required_links} links, got {len(links)}")
    
    def test_cube_model_complete(self):
        """Cube model has model.sdf + model.config."""
        self._check_model("cube", required_links=1)
    
    def test_cup_model_complete(self):
        """Cup model has model.sdf + model.config."""
        self._check_model("cup", required_links=2)  # body + handle
    
    def test_shelf_model_complete(self):
        """Shelf model has model.sdf + model.config."""
        self._check_model("shelf", required_links=6)  # 2 pillars + 3 shelves + back panel
    
    def test_table_model_complete(self):
        """Table model has model.sdf + model.config."""
        self._check_model("table", required_links=5)  # top + 4 legs
    
    def test_all_models_have_visual(self):
        """All model links have visual geometry."""
        for model_name in ["cube", "cup", "shelf", "table"]:
            with self.subTest(model=model_name):
                sdf_file = self.gazebo_dir / "models" / model_name / "model.sdf"
                root = self.parse_xml(sdf_file)
                links = root.findall(".//link")
                for link in links:
                    link_name = link.get("name", "unknown")
                    visual = link.find("visual")
                    self.assertIsNotNone(visual,
                                         f"{model_name}/{link_name}: missing visual")


# ============================================================================
# Test 4: Configuration Consistency
# ============================================================================

class TestConfigConsistency(SimTestBase):
    """Validate simulation configuration files."""
    
    def test_sim_config_yaml_exists(self):
        """sim_config.yaml exists."""
        path = self.brain_sim_dir / "config" / "sim_config.yaml"
        self.assertTrue(path.exists(), f"Missing: {path}")
    
    def test_sim_config_yaml_parseable(self):
        """sim_config.yaml is valid YAML."""
        import yaml
        path = self.brain_sim_dir / "config" / "sim_config.yaml"
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.assertIsInstance(data, dict, "sim_config.yaml should parse to dict")
    
    def test_sim_config_has_required_sections(self):
        """sim_config.yaml has required top-level sections."""
        import yaml
        path = self.brain_sim_dir / "config" / "sim_config.yaml"
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        required = ["sim", "robot", "camera", "topics", "brain_os"]
        for section in required:
            self.assertIn(section, data,
                          f"Missing section '{section}' in sim_config.yaml")
    
    def test_sensor_config_yaml_exists(self):
        """sensor_config.yaml exists."""
        path = self.brain_sim_dir / "config" / "sensor_config.yaml"
        self.assertTrue(path.exists(), f"Missing: {path}")
    
    def test_sensor_config_has_camera_sections(self):
        """sensor_config.yaml has camera and lidar sections."""
        import yaml
        path = self.brain_sim_dir / "config" / "sensor_config.yaml"
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        for section in ["camera_rgb", "camera_depth", "lidar", "imu"]:
            self.assertIn(section, data,
                          f"Missing sensor section '{section}'")
    
    def test_robot_specs_match_config(self):
        """Robot specs in SDF approximately match sim_config.yaml."""
        import yaml
        config_path = self.brain_sim_dir / "config" / "sim_config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # Kinova Gen3 should have dof (degrees of freedom) defined
        kinova = data.get("robot", {}).get("kinova_gen3", {})
        self.assertIn("dof", kinova, "kinova_gen3 config missing 'dof'")
        self.assertEqual(kinova["dof"], 7,
                        f"Expected 7 DOF, got {kinova['dof']}")
        
        # TurtleBot 4 should have max speed defined
        turtlebot = data.get("robot", {}).get("turtlebot4", {})
        self.assertIn("max_linear_vel", turtlebot,
                      "turtlebot4 config missing max_linear_vel")


# ============================================================================
# Test 5: SimBridge API (if module loads)
# ============================================================================

@unittest.skipUnless(HAS_SIM_BRIDGE, "SimBridge module not available")
class TestSimBridgeAPI(SimTestBase):
    """Test SimBridge Python API."""
    
    def test_sim_config_defaults(self):
        """SimConfig has sensible defaults."""
        config = SimConfig()
        self.assertEqual(config.physics_engine, "ode")
        self.assertEqual(config.time_step, 0.001)
        self.assertEqual(config.real_time_factor, 1.0)
        self.assertFalse(config.headless)
        self.assertTrue(config.enable_camera)
    
    def test_sim_config_custom(self):
        """SimConfig accepts custom values."""
        config = SimConfig(
            physics_engine="bullet",
            time_step=0.002,
            headless=True
        )
        self.assertEqual(config.physics_engine, "bullet")
        self.assertEqual(config.time_step, 0.002)
        self.assertTrue(config.headless)
    
    def test_create_sim_config_from_strings(self):
        """create_sim_config helper works."""
        config = create_sim_config(
            world="warehouse",
            robot="turtlebot4",
            headless=True
        )
        self.assertEqual(config.world.value, "warehouse")
        self.assertEqual(config.robot.value, "turtlebot4")
        self.assertTrue(config.headless)
    
    def test_sim_config_world_file_path(self):
        """SimConfig resolves world file path correctly."""
        config = create_sim_config(world="tabletop")
        path = Path(config.world_file_path)
        self.assertTrue(path.name.endswith(".world"),
                        f"World file should end with .world: {path.name}")
    
    def test_pose3d_defaults(self):
        """Pose3D defaults to origin."""
        pose = Pose3D()
        self.assertEqual(pose.position, [0.0, 0.0, 0.0])
        self.assertEqual(pose.orientation, [0.0, 0.0, 0.0, 1.0])
    
    def test_pose3d_custom(self):
        """Pose3D accepts custom values."""
        pose = Pose3D(
            position=[1.0, 2.0, 3.0],
            orientation=[0.0, 0.0, 0.707, 0.707]
        )
        self.assertEqual(pose.xyz, [1.0, 2.0, 3.0])
        self.assertEqual(pose.quaternion, [0.0, 0.0, 0.707, 0.707])
    
    def test_sim_object_creation(self):
        """SimObject dataclass works."""
        obj = SimObject(
            name="test_cube",
            model_type="cube",
            pose=Pose3D(position=[0.5, 0.0, 0.05]),
            mass=0.1
        )
        self.assertEqual(obj.name, "test_cube")
        self.assertEqual(obj.model_type, "cube")
        self.assertEqual(obj.mass, 0.1)
    
    def test_sim_bridge_lifecycle(self):
        """SimBridge can start, step, and stop."""
        import asyncio
        
        async def _test():
            config = create_sim_config(world="tabletop", robot="kinova_gen3")
            bridge = SimBridge(config)
            
            # Start
            await bridge.start()
            self.assertTrue(bridge.is_running)
            self.assertEqual(bridge.sim_time, 0.0)
            
            # Step
            t = await bridge.step(10)
            self.assertGreater(t, 0.0)
            self.assertEqual(bridge.step_count, 10)
            
            # Reset
            await bridge.reset()
            self.assertEqual(bridge.sim_time, 0.0)
            self.assertEqual(bridge.step_count, 0)
            
            # Stop
            await bridge.stop()
            self.assertFalse(bridge.is_running)
        
        asyncio.run(_test())
    
    def test_sim_bridge_spawn_remove(self):
        """SimBridge can spawn and remove objects."""
        import asyncio
        
        async def _test():
            config = create_sim_config(world="tabletop")
            async with SimBridge(config) as bridge:
                # Spawn
                obj = await bridge.spawn_object(
                    "cube", "my_cube",
                    position=[0.5, 0.0, 0.05],
                    mass=0.2
                )
                self.assertEqual(obj.name, "my_cube")
                self.assertEqual(len(bridge.list_objects()), 1)
                
                # Remove
                removed = await bridge.remove_object("my_cube")
                self.assertTrue(removed)
                self.assertEqual(len(bridge.list_objects()), 0)
                
                # Remove non-existent
                removed = await bridge.remove_object("ghost")
                self.assertFalse(removed)
        
        asyncio.run(_test())
    
    def test_sim_bridge_move_ee(self):
        """SimBridge move_ee_to returns expected structure."""
        import asyncio
        
        async def _test():
            config = create_sim_config(world="tabletop")
            async with SimBridge(config) as bridge:
                await bridge.start()
                
                result = await bridge.move_ee_to({
                    "position": [0.4, 0.1, 0.3],
                    "quaternion": [0, 0, 0, 1]
                })
                
                self.assertTrue(result["success"])
                self.assertIn("joint_positions", result)
                self.assertIn("time_seconds", result)
                self.assertEqual(len(result["joint_positions"]), 7)
        
        asyncio.run(_test())
    
    def test_sim_bridge_gripper(self):
        """SimBridge gripper control works."""
        import asyncio
        
        async def _test():
            config = create_sim_config(world="tabletop")
            async with SimBridge(config) as bridge:
                await bridge.start()
                
                # Open gripper
                result = await bridge.control_gripper(0.0)
                self.assertTrue(result["success"])
                self.assertFalse(result["is_grasped"])
                
                # Close enough to grasp
                result = await bridge.control_gripper(0.085)
                self.assertTrue(result["success"])
                self.assertTrue(result["is_grasped"])
                
                # Clamp to max
                result = await bridge.control_gripper(1.0)
                self.assertAlmostEqual(result["position"], 0.085, places=3)
        
        asyncio.run(_test())
    
    def test_sim_bridge_state_snapshot(self):
        """SimBridge get_state returns complete snapshot."""
        import asyncio
        
        async def _test():
            config = create_sim_config(world="tabletop")
            async with SimBridge(config) as bridge:
                await bridge.start()
                await bridge.spawn_object("cube", "obj1", position=[0.5, 0, 0.05])
                await bridge.step(50)
                
                state = await bridge.get_state()
                self.assertGreater(state.timestamp, 0.0)
                self.assertEqual(len(state.objects), 1)
                self.assertIn("arm", state.joint_states)
                self.assertIn("oakd", state.camera_frames)
                self.assertIn("rplidar", state.lidar_scans)
                
                # Verify dict serialization
                state_dict = state.to_dict()
                self.assertIn("timestamp", state_dict)
                self.assertIn("num_objects", state_dict)
        
        asyncio.run(_test())
    
    def test_sim_bridge_context_manager(self):
        """SimBridge works with async context manager."""
        import asyncio
        
        async def _test():
            config = create_sim_config()
            async with SimBridge(config) as bridge:
                self.assertTrue(bridge.is_running)
                await bridge.step(5)
                self.assertEqual(bridge.step_count, 5)
            self.assertFalse(bridge.is_running)
        
        asyncio.run(_test())
    
    def test_sim_bridge_not_started_error(self):
        """SimBridge raises RuntimeError if stepped before start."""
        import asyncio
        
        async def _test():
            bridge = SimBridge()
            with self.assertRaises(RuntimeError):
                await bridge.step(1)
        
        asyncio.run(_test())


# ============================================================================
# Test 6: Launch File Validation
# ============================================================================

class TestLaunchFiles(SimTestBase):
    """Validate ROS2 launch file."""
    
    def test_launch_file_exists(self):
        """Launch file exists and is valid Python."""
        path = self.gazebo_dir / "launch" / "tabletop.launch.py"
        self.assertTrue(path.exists(), f"Missing: {path}")
        
        # Try to compile (check syntax)
        content = path.read_text(encoding="utf-8")
        compile(content, str(path), "exec")
    
    def test_launch_file_has_generate_function(self):
        """Launch file has generate_launch_description()."""
        path = self.gazebo_dir / "launch" / "tabletop.launch.py"
        content = path.read_text(encoding="utf-8")
        self.assertIn("generate_launch_description", content)
        self.assertIn("LaunchDescription", content)
    
    def test_launch_file_declares_world_arg(self):
        """Launch file declares 'world' launch argument."""
        path = self.gazebo_dir / "launch" / "tabletop.launch.py"
        content = path.read_text(encoding="utf-8")
        self.assertIn("world", content.lower())
    
    def test_launch_file_declares_robot_arg(self):
        """Launch file declares 'robot' launch argument."""
        path = self.gazebo_dir / "launch" / "tabletop.launch.py"
        content = path.read_text(encoding="utf-8")
        self.assertIn("robot", content.lower())


# ============================================================================
# Test 7: Demo Integrity
# ============================================================================

class TestDemoIntegrity(SimTestBase):
    """Validate the E2E demo script."""
    
    def test_demo_script_exists(self):
        """E2E demo script exists."""
        path = self.brain_sim_dir / "demo" / "e2e_demo.py"
        self.assertTrue(path.exists(), f"Missing: {path}")
    
    def test_demo_script_is_valid_python(self):
        """E2E demo is valid Python."""
        path = self.brain_sim_dir / "demo" / "e2e_demo.py"
        content = path.read_text(encoding="utf-8")
        compile(content, str(path), "exec")
    
    def test_demo_has_required_scenarios(self):
        """Demo defines all 4 scenarios."""
        path = self.brain_sim_dir / "demo" / "e2e_demo.py"
        content = path.read_text(encoding="utf-8")
        scenarios = ["pick_cup", "stack_boxes", "inspect_arm", "wild_goose"]
        for s in scenarios:
            self.assertIn(s, content, f"Demo missing scenario: {s}")
    
    def test_demo_has_6_stage_pipeline(self):
        """Demo has 6-stage pipeline labels."""
        path = self.brain_sim_dir / "demo" / "e2e_demo.py"
        content = path.read_text(encoding="utf-8")
        stages = ["Stage 0", "Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5"]
        for s in stages:
            self.assertIn(s, content, f"Demo missing stage: {s}")


# ============================================================================
# Runner
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Brain OS Simulation Test Suite")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Verbose output")
    args = parser.parse_args()
    
    verbosity = 2 if args.verbose else 1
    unittest.main(verbosity=verbosity, argv=[sys.argv[0]])
