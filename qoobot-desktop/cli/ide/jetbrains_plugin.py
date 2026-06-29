"""
JetBrains Plugin Bridge — v1.6+

Generates IntelliJ platform plugin configuration for PyCharm/CLion integration.
Provides:
- PyCharm plugin: QooBot Python SDK autocompletion, skill project templates, debug config
- CLion plugin: C++/Python mixed debugging, CMake integration, qoocore model compilation
- Project import: one-click import of QooBot skill/service/model projects
- Run configurations: simulation launch, remote debug, test runner presets
- Tool window: behavior tree viewer, sensor data inspector, profiler charts

Architecture:
    This module generates plugin.xml + Java/Kotlin source scaffolding for the
    JetBrains IntelliJ Platform SDK. The actual plugin is built as a separate
    Gradle project; this module provides the configuration bridge and CLI commands.

Reference: https://plugins.jetbrains.com/docs/intellij/welcome.html
"""

from __future__ import annotations

import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

console = Console()


# ============================================================================
# Data Models
# ============================================================================

class JetBrainsIDE(Enum):
    """Supported JetBrains IDEs."""
    PYCHARM = "pycharm"
    CLION = "clion"
    IDEA = "idea"  # IntelliJ IDEA Ultimate (polyglot)


class DebuggerBackend(Enum):
    """Debug backend for mixed-language debugging."""
    GDB = "gdb"
    LLDB = "lldb"
    PDB = "pdb"  # Python only
    MIXED = "mixed"  # GDB + pydevd bridge


@dataclass
class PluginManifest:
    """JetBrains plugin.xml manifest data."""
    id: str = "com.qoobot.qoodev"
    name: str = "QooBot Developer Tools"
    version: str = "1.6.0"
    vendor: str = "QooBot"
    description: str = "QooBot Humanoid Robot Development Toolkit — PyCharm/CLion Integration"
    since_build: str = "232"  # IntelliJ 2023.2+
    until_build: str = "242.*"
    idea_versions: List[str] = field(default_factory=lambda: [
        "pycharm-community-2023.2+",
        "pycharm-professional-2023.2+",
        "clion-2023.2+",
    ])
    dependencies: List[str] = field(default_factory=lambda: [
        "com.intellij.modules.platform",
        "com.intellij.modules.python",
        "com.intellij.modules.cidr.lang",  # C/C++ for CLion
    ])
    actions: List[Dict[str, str]] = field(default_factory=list)
    extensions: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class RunConfiguration:
    """Pre-configured run/debug configuration."""
    name: str
    type: str  # "python", "cmake", "gdb", "remote"
    script_path: Optional[str] = None
    cmake_target: Optional[str] = None
    working_dir: str = "$PROJECT_DIR$"
    env_vars: Dict[str, str] = field(default_factory=dict)
    debugger: DebuggerBackend = DebuggerBackend.MIXED
    remote_host: Optional[str] = None
    remote_port: Optional[int] = None


@dataclass
class ProjectTemplate:
    """JetBrains project template definition."""
    name: str
    description: str
    category: str  # "skill", "service", "model"
    files: List[Tuple[str, str]] = field(default_factory=list)  # (path, content_template)


# ============================================================================
# Plugin Generator
# ============================================================================

class JetBrainsPlugin:
    """Generates JetBrains IDE plugin configuration and project scaffolding.

    Usage:
        plugin = JetBrainsPlugin(Path("/path/to/qoodev"))
        plugin.generate_config()           # Generate plugin.xml
        plugin.generate_run_configs()      # Generate run configurations
        plugin.generate_templates()        # Generate project templates
        plugin.generate_tool_windows()     # Generate tool window configs
    """

    # Predefined run configurations
    _PRESET_RUN_CONFIGS: List[RunConfiguration] = [
        RunConfiguration(
            name="QooBot — Simulation (Isaac Sim)",
            type="python",
            script_path="$PROJECT_DIR$/qoodev/cli/main.py",
            env_vars={"QOOBOT_SIM_BACKEND": "isaac_sim", "QOOBOT_DEBUG": "1"},
            debugger=DebuggerBackend.PDB,
        ),
        RunConfiguration(
            name="QooBot — Simulation (MuJoCo)",
            type="python",
            script_path="$PROJECT_DIR$/qoodev/cli/main.py",
            env_vars={"QOOBOT_SIM_BACKEND": "mujoco", "QOOBOT_DEBUG": "1"},
            debugger=DebuggerBackend.PDB,
        ),
        RunConfiguration(
            name="QooBot — Mixed Debug (GDB + Python)",
            type="gdb",
            script_path="$PROJECT_DIR$/qoodev/cli/main.py",
            env_vars={"QOOBOT_DEBUG": "1", "QOOBOT_GDB": "1"},
            debugger=DebuggerBackend.MIXED,
        ),
        RunConfiguration(
            name="QooBot — Remote Debug (Robot)",
            type="remote",
            remote_host="qoobot.local",
            remote_port=5678,
            env_vars={"QOOBOT_REMOTE": "1"},
            debugger=DebuggerBackend.LLDB,
        ),
        RunConfiguration(
            name="QooBot — Unit Tests",
            type="python",
            script_path="$PROJECT_DIR$/tests/",
            env_vars={"QOOBOT_TEST": "1"},
            debugger=DebuggerBackend.PDB,
        ),
        RunConfiguration(
            name="qoocore — Model Compile & Profile",
            type="python",
            script_path="$PROJECT_DIR$/qoodev/cli/main.py",
            working_dir="$PROJECT_DIR$",
            env_vars={"QOOBOT_COMPILE": "1"},
            debugger=DebuggerBackend.PDB,
        ),
    ]

    def __init__(self, project_root: Path, ide: JetBrainsIDE = JetBrainsIDE.PYCHARM):
        self.project_root = Path(project_root)
        self.ide = ide
        self._idea_dir = self.project_root / ".idea"
        self._manifest = PluginManifest()

    # ── Plugin XML Generation ───────────────────────────────────────────────

    def generate_config(self) -> Path:
        """Generate the full JetBrains plugin configuration.

        Creates:
            .idea/qoodev.xml           — Plugin settings
            .idea/runConfigurations/    — Run/debug presets
            .idea/codeStyles/           — Code style settings
            .idea/inspectionProfiles/   — Inspection profiles

        Returns:
            Path to the generated .idea directory.
        """
        console.print(Panel.fit(
            f"[bold cyan]Generating JetBrains Plugin Config[/bold cyan]\n"
            f"IDE: [yellow]{self.ide.value}[/yellow]  "
            f"Project: [dim]{self.project_root.name}[/dim]",
            border_style="cyan",
        ))

        self._idea_dir.mkdir(parents=True, exist_ok=True)
        files_created: List[Path] = []

        # 1. Plugin settings XML
        files_created.append(self._write_plugin_settings())
        # 2. Run configurations
        files_created.extend(self._write_run_configs())
        # 3. Code style
        files_created.append(self._write_code_style())
        # 4. File templates
        files_created.extend(self._write_file_templates())
        # 5. External tools (qoo CLI integration)
        files_created.append(self._write_external_tools())
        # 6. Inspection profiles
        files_created.append(self._write_inspections())
        # 7. GDB/LLDB debug config (CLion)
        if self.ide == JetBrainsIDE.CLION:
            files_created.append(self._write_native_debug_config())

        self._print_summary(files_created)
        return self._idea_dir

    def _write_plugin_settings(self) -> Path:
        """Write qoodev.xml plugin settings."""
        root = ET.Element("application")
        component = ET.SubElement(root, "component", name="QooBotSettings")

        ET.SubElement(component, "option", name="sdkPath",
                       value=str(self.project_root / "qoobot-sdk"))
        ET.SubElement(component, "option", name="simBackend",
                       value="mujoco")
        ET.SubElement(component, "option", name="qooPath",
                       value=str(self.project_root / "qoodev" / "cli" / "main.py"))
        ET.SubElement(component, "option", name="enableMixedDebug",
                       value="true")
        ET.SubElement(component, "option", name="enableTelemetry",
                       value="false")
        ET.SubElement(component, "option", name="robotHost",
                       value="qoobot.local")

        file_path = self._idea_dir / "qoodev.xml"
        self._write_xml(root, file_path)
        return file_path

    def _write_run_configs(self) -> List[Path]:
        """Write run/debug configuration XML files."""
        configs_dir = self._idea_dir / "runConfigurations"
        configs_dir.mkdir(parents=True, exist_ok=True)
        created: List[Path] = []

        for rc in self._PRESET_RUN_CONFIGS:
            safe_name = rc.name.replace(" ", "_").replace("—", "-").replace("(", "").replace(")", "")
            file_path = configs_dir / f"{safe_name}.xml"
            root = ET.Element("component", name="ProjectRunConfigurationManager")

            config = ET.SubElement(root, "configuration",
                                   default="false",
                                   name=rc.name,
                                   type="PythonConfigurationType",
                                   factoryName="Python")

            if rc.script_path:
                ET.SubElement(config, "option", name="scriptName",
                               value=rc.script_path)
            ET.SubElement(config, "option", name="workingDirectory",
                           value=rc.working_dir)

            envs_elem = ET.SubElement(config, "envs")
            for key, val in rc.env_vars.items():
                ET.SubElement(envs_elem, "env", name=key, value=val)

            # Debug settings
            if rc.debugger == DebuggerBackend.MIXED:
                ET.SubElement(config, "option", name="debugger",
                               value="com.qoobot.mixedDebugger")

            ET.SubElement(config, "method", v="2")

            self._write_xml(root, file_path)
            created.append(file_path)

        return created

    def _write_code_style(self) -> Path:
        """Write QooBot code style settings for Python + C++."""
        styles_dir = self._idea_dir / "codeStyles"
        styles_dir.mkdir(parents=True, exist_ok=True)

        content = """<component name="ProjectCodeStyleConfiguration">
  <code_scheme name="QooBot" version="173">
    <option name="LINE_SEPARATOR" value="&#10;" />
    <option name="RIGHT_MARGIN" value="120" />
    <Python>
      <option name="TAB_SIZE" value="4" />
      <option name="USE_TABS" value="false" />
      <option name="OPTIMIZE_IMPORTS_ALWAYS" value="true" />
      <option name="HANG_CLOSING_BRACKETS" value="true" />
    </Python>
    <ObjectiveC>
      <option name="INDENT_NAMESPACE_MEMBERS" value="0" />
      <option name="INDENT_C_STRUCT_MEMBERS" value="2" />
      <option name="INDENT_CLASS_MEMBERS" value="2" />
      <option name="HEADER_GUARD_STYLE_PATTERN" value="${PROJECT_NAME}_${FILE_NAME}_${EXT}" />
    </ObjectiveC>
    <codeStyleSettings language="Python">
      <option name="RIGHT_MARGIN" value="120" />
      <option name="ALIGN_MULTILINE_PARAMETERS" value="false" />
      <option name="CALL_PARAMETERS_WRAP" value="1" />
      <option name="METHOD_PARAMETERS_WRAP" value="1" />
    </codeStyleSettings>
    <codeStyleSettings language="ObjectiveC">
      <option name="RIGHT_MARGIN" value="120" />
      <option name="BRACE_STYLE" value="2" />
      <option name="CLASS_BRACE_STYLE" value="2" />
      <option name="FUNCTION_BRACE_STYLE" value="2" />
      <option name="CATCH_ON_NEW_LINE" value="true" />
    </codeStyleSettings>
  </code_scheme>
</component>"""
        file_path = styles_dir / "Project.xml"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def _write_file_templates(self) -> List[Path]:
        """Write file templates for QooBot project types."""
        templates_dir = self._idea_dir / "fileTemplates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        templates = {
            "QooBot Skill.py": '''"""
${NAME} - QooBot Skill

Author: ${USER}
Created: ${DATE}

Description:
    ${DESCRIPTION}
"""

from qoobot_sdk.skill import QooSkill
from qoobot_sdk.perception import Camera, LiDAR
from qoobot_sdk.control import JointController, Gripper
from qoobot_sdk.communication import Publisher, Subscriber


class ${NAME}(QooSkill):
    """${DESCRIPTION}"""

    def __init__(self):
        super().__init__(
            name="${NAME}",
            version="0.1.0",
        )

    def setup(self) -> None:
        """Initialize sensors and controllers."""
        self.camera = Camera("rgb_front")
        self.lidar = LiDAR("os1_64")
        self.arm = JointController("right_arm")
        self.gripper = Gripper("right_hand")

    def run(self) -> None:
        """Main skill loop."""
        self.logger.info(f"${NAME} started")
        while self.running:
            # Perception
            image = self.camera.capture()
            points = self.lidar.scan()

            # Cognition & Planning
            # TODO: Implement your logic here

            # Control
            # self.arm.move_to(...)
            # self.gripper.close()

            self.sleep(0.01)  # 100 Hz control loop

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info(f"${NAME} stopped")
''',
            "QooBot Service.cpp": '''/**
 * ${NAME} - QooBot System Service
 *
 * Author: ${USER}
 * Created: ${DATE}
 *
 * Description:
 *     ${DESCRIPTION}
 */

#include <qoobot/qoobot.h>
#include <qoobot/perception/camera.h>
#include <qoobot/control/joint_controller.h>

#include <memory>
#include <chrono>

using namespace qoobot;
using namespace std::chrono_literals;

class ${NAME} : public QooService {
public:
    ${NAME}() : QooService("${NAME}") {}

    bool init() override {
        camera_ = std::make_unique<Camera>("rgb_front");
        arm_ = std::make_unique<JointController>("right_arm");

        QOOBOT_LOG_INFO("${NAME} initialized");
        return true;
    }

    void run() override {
        QOOBOT_LOG_INFO("${NAME} running at {} Hz", frequency());

        while (running()) {
            auto image = camera_->capture();
            // TODO: Implement service logic

            std::this_thread::sleep_for(
                std::chrono::microseconds(static_cast<int>(1e6 / frequency()))
            );
        }
    }

    void cleanup() override {
        QOOBOT_LOG_INFO("${NAME} stopped");
    }

private:
    std::unique_ptr<Camera> camera_;
    std::unique_ptr<JointController> arm_;
};

REGISTER_QOO_SERVICE(${NAME})
''',
            "QooBot Model.py": '''"""
${NAME} - QooBot AI Model

Author: ${USER}
Created: ${DATE}

Description:
    ${DESCRIPTION}
"""

import torch
import torch.nn as nn
from qoobot_sdk.skill import QooSkill


class ${NAME}(nn.Module):
    """${DESCRIPTION}"""

    def __init__(self):
        super().__init__()
        # TODO: Define your model architecture
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, padding=1)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass."""
        x = self.conv1(x)
        x = self.relu(x)
        return x


class ${NAME}Skill(QooSkill):
    """Skill wrapper for the ${NAME} model."""

    def __init__(self):
        super().__init__(
            name="${NAME}",
            version="0.1.0",
        )
        self.model = ${NAME}()

    def setup(self) -> None:
        """Load model weights."""
        # Load .qoomodel or .pth weights
        self.model.eval()

    def run(self) -> None:
        """Inference loop."""
        while self.running:
            # Get input tensor
            # output = self.model(input_tensor)
            self.sleep(0.01)
''',
        }

        created: List[Path] = []
        for filename, content in templates.items():
            file_path = templates_dir / filename
            file_path.write_text(content, encoding="utf-8")
            created.append(file_path)

        return created

    def _write_external_tools(self) -> Path:
        """Write external tool configurations for qoo CLI."""
        root = ET.Element("component", name="ExternalToolsManager")

        tools = [
            ("qoo build", "Build QooBot project", "$ProjectFileDir$", "qoo build"),
            ("qoo test", "Run QooBot tests", "$ProjectFileDir$", "qoo test"),
            ("qoo sim (MuJoCo)", "Launch MuJoCo simulation", "$ProjectFileDir$",
             "qoo sim start --backend mujoco"),
            ("qoo package", "Package QooBot skill", "$ProjectFileDir$", "qoo package"),
            ("qoo profile", "Profile model latency", "$ProjectFileDir$", "qoo profile model"),
            ("qoo compile", "Compile model to .qoomodel", "$ProjectFileDir$", "qoo compile"),
            ("qoo annotate", "Launch annotation tool", "$ProjectFileDir$", "qoo annotate"),
        ]

        tools_elem = ET.SubElement(root, "tools")
        for name, desc, workdir, cmd in tools:
            tool = ET.SubElement(tools_elem, "tool",
                                 name=name,
                                 description=desc,
                                 showInMainMenu="true",
                                 showInEditor="true",
                                 showInProject="true",
                                 showInSearchPopup="true",
                                 disabled="false",
                                 useConsole="true",
                                 showConsoleOnStdOut="true",
                                 showConsoleOnStdErr="true",
                                 synchronizeAfterRun="true")
            ET.SubElement(tool, "exec",
                          program="qoo",
                          parameters=cmd.split()[1:],
                          workingDirectory=workdir)

        file_path = self._idea_dir / "externalTools.xml"
        self._write_xml(root, file_path)
        return file_path

    def _write_inspections(self) -> Path:
        """Write inspection profiles for QooBot code quality."""
        profiles_dir = self._idea_dir / "inspectionProfiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)

        content = """<component name="InspectionProjectProfileManager">
  <profile version="1.0">
    <option name="myName" value="QooBot" />
    <inspection_tool class="PyPackageRequirementsInspection" enabled="true" level="WARNING" />
    <inspection_tool class="PyPep8NamingInspection" enabled="true" level="WEAK WARNING" />
    <inspection_tool class="PyUnresolvedReferencesInspection" enabled="true" level="WARNING" />
    <inspection_tool class="SpellCheckingInspection" enabled="false" level="TYPO" />
    <inspection_tool class="ClangTidy" enabled="true" level="WARNING" />
    <inspection_tool class="OCUnusedGlobalDeclaration" enabled="true" level="WARNING" />
    <inspection_tool class="OCUnusedMacro" enabled="true" level="WARNING" />
  </profile>
</component>"""
        file_path = profiles_dir / "QooBot.xml"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def _write_native_debug_config(self) -> Path:
        """Write CLion-specific native debug configuration."""
        configs_dir = self._idea_dir / "runConfigurations"
        configs_dir.mkdir(parents=True, exist_ok=True)

        content = """<component name="ProjectRunConfigurationManager">
  <configuration default="false" name="QooBot — CLion Mixed Debug" type="CMakeRunConfiguration" factoryName="Application" REDIRECT_INPUT="false" ELEVATE="false" USE_EXTERNAL_CONSOLE="false" EMULATE_TERMINAL="false" PASS_PARENT_ENVS_2="true" PROJECT_NAME="qoobot" TARGET_NAME="qoodev" CONFIG_NAME="Debug" RUN_TARGET_PROJECT_NAME="qoobot" RUN_TARGET_NAME="qoodev">
    <method v="2">
      <option name="com.qoobot.mixedDebugger" enabled="true" />
      <option name="GDBDebugger" enabled="true" />
      <option name="com.jetbrains.python.debugger.PyDebugger" enabled="true" />
    </method>
  </configuration>
</component>"""
        file_path = configs_dir / "QooBot_CLion_Mixed_Debug.xml"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    # ── Project Template Generation ─────────────────────────────────────────

    def generate_templates(self) -> List[ProjectTemplate]:
        """Generate JetBrains project templates for File | New | Project."""
        templates = [
            ProjectTemplate(
                name="QooBot Skill (Python)",
                description="Create a new QooBot robot skill using Python SDK",
                category="skill",
                files=[
                    ("__init__.py", "# ${NAME} skill package\n"),
                    ("skill.py", self._get_template_content("QooBot Skill.py")),
                    ("manifest.yaml", self._get_skill_manifest_template()),
                ],
            ),
            ProjectTemplate(
                name="QooBot Service (C++)",
                description="Create a new QooBot system service in C++17",
                category="service",
                files=[
                    ("CMakeLists.txt", self._get_cmake_template()),
                    ("main.cpp", self._get_template_content("QooBot Service.cpp")),
                    ("config.yaml", "# ${NAME} service configuration\n"),
                ],
            ),
            ProjectTemplate(
                name="QooBot Model (PyTorch)",
                description="Create a new QooBot AI model project with PyTorch",
                category="model",
                files=[
                    ("__init__.py", "# ${NAME} model package\n"),
                    ("model.py", self._get_template_content("QooBot Model.py")),
                    ("train.py", "# Training script for ${NAME}\n"),
                    ("config.yaml", self._get_model_config_template()),
                ],
            ),
        ]
        return templates

    def generate_run_configs(self) -> List[RunConfiguration]:
        """Return predefined run configurations."""
        return list(self._PRESET_RUN_CONFIGS)

    def generate_tool_windows(self) -> Dict[str, Any]:
        """Generate tool window configurations for the IDE plugin."""
        return {
            "behaviorTreeViewer": {
                "id": "QooBot Behavior Tree",
                "anchor": "right",
                "icon": "qoobot_bt.svg",
                "factoryClass": "com.qoobot.qoodev.toolwindow.BehaviorTreeToolWindowFactory",
            },
            "sensorInspector": {
                "id": "QooBot Sensor Inspector",
                "anchor": "bottom",
                "icon": "qoobot_sensor.svg",
                "factoryClass": "com.qoobot.qoodev.toolwindow.SensorInspectorFactory",
            },
            "profilerCharts": {
                "id": "QooBot Profiler",
                "anchor": "bottom",
                "icon": "qoobot_profile.svg",
                "factoryClass": "com.qoobot.qoodev.toolwindow.ProfilerToolWindowFactory",
            },
            "simControl": {
                "id": "QooBot Sim Control",
                "anchor": "left",
                "icon": "qoobot_sim.svg",
                "factoryClass": "com.qoobot.qoodev.toolwindow.SimControlFactory",
            },
        }

    # ── Plugin Manifest ─────────────────────────────────────────────────────

    def generate_plugin_xml(self) -> str:
        """Generate the plugin.xml content for the JetBrains plugin."""
        return f"""<idea-plugin>
    <id>{self._manifest.id}</id>
    <name>{self._manifest.name}</name>
    <version>{self._manifest.version}</version>
    <vendor email="dev@qoobot.ai" url="https://qoobot.ai">{self._manifest.vendor}</vendor>

    <description><![CDATA[
        <h2>QooBot Developer Tools for JetBrains IDEs</h2>
        <p>Full-featured development toolkit for QooBot Humanoid Robot:</p>
        <ul>
            <li>Python/C++ mixed debugging with GDB/LLDB bridge</li>
            <li>Behavior tree visual editor with real-time preview</li>
            <li>Sensor data inspector (camera, LiDAR, IMU streams)</li>
            <li>Performance profiler integration (qoocore flame graphs)</li>
            <li>Simulation launch & control (Isaac Sim / MuJoCo)</li>
            <li>One-click model compilation to .qoomodel format</li>
            <li>Skill packaging & qoostore submission</li>
        </ul>
        <p>Supports PyCharm Community/Professional 2023.2+ and CLion 2023.2+.</p>
    ]]></description>

    <change-notes><![CDATA[
        <h3>v1.6.0</h3>
        <ul>
            <li>Initial PyCharm/CLion plugin bridge</li>
            <li>Mixed Python/C++ debugging support</li>
            <li>Pre-configured run/debug configurations</li>
            <li>Project templates for skill/service/model</li>
            <li>qoo CLI external tools integration</li>
        </ul>
    ]]></change-notes>

    <idea-version since-build="{self._manifest.since_build}" until-build="{self._manifest.until_build}"/>

    <depends>com.intellij.modules.platform</depends>
    <depends>com.intellij.modules.python</depends>
    <depends optional="true" config-file="qoodev-clion.xml">com.intellij.modules.cidr.lang</depends>

    <extensions defaultExtensionNs="com.intellij">
        <!-- Project templates -->
        <projectTemplate
            implementation="com.qoobot.qoodev.templates.QooBotSkillTemplate"/>
        <projectTemplate
            implementation="com.qoobot.qoodev.templates.QooBotServiceTemplate"/>
        <projectTemplate
            implementation="com.qoobot.qoodev.templates.QooBotModelTemplate"/>

        <!-- Tool windows -->
        <toolWindow id="QooBot Behavior Tree" anchor="right"
                    factoryClass="com.qoobot.qoodev.toolwindow.BehaviorTreeToolWindowFactory"
                    icon="/icons/qoobot_bt.svg"/>
        <toolWindow id="QooBot Sensor Inspector" anchor="bottom"
                    factoryClass="com.qoobot.qoodev.toolwindow.SensorInspectorFactory"
                    icon="/icons/qoobot_sensor.svg"/>
        <toolWindow id="QooBot Profiler" anchor="bottom"
                    factoryClass="com.qoobot.qoodev.toolwindow.ProfilerToolWindowFactory"
                    icon="/icons/qoobot_profile.svg"/>

        <!-- File type: Behavior Tree JSON -->
        <fileType name="QooBot Behavior Tree" implementation="com.qoobot.qoodev.filetype.BTreeFileType"
                  fieldName="INSTANCE" language="JSON" extensions="btree.json"/>

        <!-- Run configuration producers -->
        <runConfigurationProducer
            implementation="com.qoobot.qoodev.run.QooBotSimRunConfigProducer"/>
        <runConfigurationProducer
            implementation="com.qoobot.qoodev.run.QooBotTestRunConfigProducer"/>

        <!-- Debugger -->
        <xdebugger.debuggerImplementation
            implementation="com.qoobot.qoodev.debug.QooBotMixedDebugger"/>
    </extensions>

    <actions>
        <group id="QooBot.MainMenu" text="QooBot" description="QooBot development actions">
            <action id="QooBot.Build" class="com.qoobot.qoodev.actions.BuildAction"
                    text="Build Project" description="Build QooBot project"/>
            <action id="QooBot.SimStart" class="com.qoobot.qoodev.actions.SimStartAction"
                    text="Start Simulation" description="Launch QooBot simulation"/>
            <action id="QooBot.Package" class="com.qoobot.qoodev.actions.PackageAction"
                    text="Package Skill" description="Package skill as .qooskills"/>
            <action id="QooBot.Profile" class="com.qoobot.qoodev.actions.ProfileAction"
                    text="Profile Model" description="Run latency profiler"/>
            <add-to-group group-id="ToolsMenu" anchor="last"/>
        </group>
    </actions>
</idea-plugin>"""

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _write_xml(self, root: ET.Element, file_path: Path) -> None:
        """Write an ElementTree to file with proper indentation."""
        ET.indent(root, space="  ")
        tree = ET.ElementTree(root)
        tree.write(str(file_path), encoding="utf-8", xml_declaration=True)

    def _get_skill_manifest_template(self) -> str:
        return """# ${NAME} Skill Manifest
name: ${NAME}
version: 0.1.0
author: ${USER}
description: ${DESCRIPTION}
category: manipulation
permissions:
  - camera.rgb_front
  - control.right_arm
  - control.right_hand
privacy_labels:
  - camera_data: "Used for object detection"
dependencies:
  qoobot-sdk: ">=0.1.0"
min_robot_firmware: "1.0.0"
"""

    def _get_model_config_template(self) -> str:
        return """# ${NAME} Model Configuration
model:
  name: ${NAME}
  version: 0.1.0
  framework: pytorch
  input_shape: [1, 3, 224, 224]
  output_classes: 1000

training:
  batch_size: 32
  epochs: 100
  learning_rate: 0.001
  optimizer: adam
  scheduler: cosine

compilation:
  target: qoomodel
  precision: int8  # int8 | fp16 | fp32
  backend: auto     # auto | cpu | gpu | npu
"""

    def _get_cmake_template(self) -> str:
        return """cmake_minimum_required(VERSION 3.20)
project(${NAME} VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(qoobot REQUIRED)
find_package(qoocore REQUIRED)

add_executable(${NAME}
    main.cpp
)

target_link_libraries(${NAME} PRIVATE
    qoobot::qoobot
    qoocore::qoocore
)

target_compile_options(${NAME} PRIVATE
    -Wall -Wextra -Wpedantic
)
"""

    def _get_template_content(self, filename: str) -> str:
        """Read template content from fileTemplates directory."""
        templates_dir = self._idea_dir / "fileTemplates"
        file_path = templates_dir / filename
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        return f"# TODO: {filename}\n"

    def _print_summary(self, files: List[Path]) -> None:
        """Print a summary of generated files."""
        tree = Tree(f"[bold green]✓[/bold green] Generated {len(files)} JetBrains config files")
        for f in files:
            tree.add(f"[dim]{f.relative_to(self.project_root)}[/dim]")
        console.print(tree)

    # ── CLI Integration ─────────────────────────────────────────────────────

    @staticmethod
    def install_to_ide(project_root: Path, ide: JetBrainsIDE = JetBrainsIDE.PYCHARM) -> bool:
        """Install the generated config into the IDE's config directory.

        Copies .idea/ files to the appropriate IDE config location.
        """
        plugin = JetBrainsPlugin(project_root, ide)
        idea_dir = plugin.generate_config()

        # Determine IDE config path
        ide_configs = {
            JetBrainsIDE.PYCHARM: Path.home() / ".PyCharm" / "config",
            JetBrainsIDE.CLION: Path.home() / ".CLion" / "config",
            JetBrainsIDE.IDEA: Path.home() / ".IntelliJIdea" / "config",
        }

        config_path = ide_configs.get(ide)
        if config_path and config_path.exists():
            dest = config_path / "project-templates" / "QooBot"
            shutil.copytree(idea_dir, dest, dirs_exist_ok=True)
            console.print(f"[green]✓[/green] Installed to: [bold]{dest}[/bold]")
            return True

        console.print(f"[yellow]⚠[/yellow] IDE config not found at {config_path}")
        return False
