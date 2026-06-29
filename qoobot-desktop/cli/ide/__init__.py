"""
qoodev IDE Integration Module — v1.6+

Provides JetBrains IDE plugin support (PyCharm/CLion) and advanced IDE features:
- JetBrains plugin bridge (PyCharm/CLion C++/Python mixed debugging)
- Skill manifest editor (metadata, permissions, privacy labels)
- Code generator (sensor config, behavior tree, model skeleton generation)

Usage:
    from qoodev.ide import JetBrainsPlugin, SkillManifestEditor, CodeGenerator

    # Generate a JetBrains plugin config
    plugin = JetBrainsPlugin(project_root)
    plugin.generate_config()

    # Edit skill manifest
    editor = SkillManifestEditor("my_skill")
    editor.open()
"""

from qoodev.ide.jetbrains_plugin import JetBrainsPlugin
from qoodev.ide.skill_manifest_editor import SkillManifestEditor
from qoodev.ide.code_generator import CodeGenerator

__all__ = ["JetBrainsPlugin", "SkillManifestEditor", "CodeGenerator"]
