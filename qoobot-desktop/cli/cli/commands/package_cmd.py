"""qoo test CLI — 测试命令"""

from pathlib import Path
from typer import Typer, Option, Argument
from typing import Optional, List

app = Typer(name="test", help="Run unit tests and regression tests")


@app.command("run")
def run_tests(
    project_dir: str = Argument(".", help="Project root directory"),
    tags: Optional[List[str]] = Option(None, "--tag", "-t", help="Filter tests by tag"),
    verbose: bool = Option(False, "--verbose", "-v", help="Verbose output"),
    junit_xml: Optional[str] = Option(None, "--junit", help="Output JUnit XML report"),
    timeout: float = Option(30.0, "--timeout", help="Default test timeout (seconds)"),
):
    """Run unit tests for the current project"""
    import sys
    import importlib.util

    project_path = Path(project_dir).resolve()
    test_dir = project_path / "tests"

    if not test_dir.exists():
        print(f"❌ No tests/ directory found in {project_path}")
        raise SystemExit(1)

    # 动态加载测试文件
    sys.path.insert(0, str(project_path))

    from qoodev.testing import SkillTestRunner, TestResult

    runner = SkillTestRunner()

    # 自动发现测试
    test_count = 0
    for test_file in sorted(test_dir.rglob("test_*.py")):
        module_name = str(test_file.relative_to(project_path)).replace("/", ".").replace("\\", ".").replace(".py", "")
        try:
            spec = importlib.util.spec_from_file_location(module_name, test_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            test_count += 1
        except Exception as e:
            print(f"⚠️  Failed to load {test_file}: {e}")

    if test_count == 0:
        print("❌ No test files found (test_*.py)")
        raise SystemExit(1)

    results = runner.run_all(tags=list(tags) if tags else None)

    # 生成 JUnit XML
    if junit_xml:
        _write_junit_xml(results, Path(junit_xml))

    # 退出码
    failed = sum(1 for r in results.values() if r["status"] != TestResult.PASS)
    if failed > 0:
        raise SystemExit(1)


@app.command("regression")
def regression(
    project_dir: str = Argument(".", help="Project root directory"),
    scenario: str = Option("all", "--scenario", "-s", help="Scenario name or 'all'"),
    output: Optional[str] = Option(None, "--output", "-o", help="Output report path"),
):
    """Run simulation regression tests"""
    from qoodev.testing import RegressionTestSuite, create_home_scenario, create_factory_scenario

    suite = RegressionTestSuite(name="skill-regression")

    if scenario in ("all", "home"):
        suite.add_scenario(create_home_scenario())
    if scenario in ("all", "factory"):
        suite.add_scenario(create_factory_scenario())

    results = suite.run_all()

    if output:
        import json
        with open(output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"📊 Report saved: {output}")

    total_failed = sum(r.get("failed", 0) for r in results.values())
    if total_failed > 0:
        raise SystemExit(1)


@app.command("scaffold")
def scaffold(
    project_dir: str = Argument(".", help="Project root directory"),
):
    """Generate test scaffolding for the current project"""
    project_path = Path(project_dir).resolve()

    tests_dir = project_path / "tests"
    tests_dir.mkdir(exist_ok=True)

    # 生成 conftest.py
    conftest = tests_dir / "conftest.py"
    if not conftest.exists():
        conftest.write_text("""# Test fixtures and configuration
from qoodev.testing import (
    SkillTestRunner,
    TestScenario,
    create_home_scenario,
    create_factory_scenario,
    MockCamera,
    MockLidar,
    MockIMU,
    MockJointActuator,
    MockGripper,
    MockMobileBase,
)

import pytest


@pytest.fixture
def home_scenario():
    return create_home_scenario()


@pytest.fixture
def factory_scenario():
    return create_factory_scenario()


@pytest.fixture
def runner(home_scenario):
    return SkillTestRunner(home_scenario)
""", encoding="utf-8")
        print(f"✅ Created: {conftest}")

    # 生成示例测试
    example_test = tests_dir / "test_skill_example.py"
    if not example_test.exists():
        example_test.write_text("""# Example skill test
from qoodev.testing import SkillTestRunner, create_home_scenario

scenario = create_home_scenario()
runner = SkillTestRunner(scenario)


@runner.register("test_camera_data", description="Verify camera mock returns valid data")
def test_camera(scenario):
    cam = scenario.cameras["head_camera"]
    cam.inject_image()
    data = cam.get_data()
    assert data is not None
    assert "rgb" in data
    assert "depth" in data


@runner.register("test_joint_control", description="Verify joint actuator mock records commands")
def test_joint_control(scenario):
    arm = scenario.joint_actuators["arm"]
    arm.set_position_targets({"shoulder_pan": 0.5, "elbow": -0.3})
    assert arm.command_count == 1
    assert arm.get_positions()["shoulder_pan"] == 0.5


@runner.register("test_gripper_cycle", description="Verify gripper grasp/release cycle")
def test_gripper_cycle(scenario):
    grip = scenario.grippers["gripper"]
    grip.grasp(force=15.0)
    assert grip._has_object
    grip.release()
    assert not grip._has_object


if __name__ == "__main__":
    runner.run_all()
""", encoding="utf-8")
        print(f"✅ Created: {example_test}")

    # 生成 pytest.ini
    pytest_ini = project_path / "pytest.ini"
    if not pytest_ini.exists():
        pytest_ini.write_text("""[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
timeout = 60
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    simulation: marks tests that require simulation
""", encoding="utf-8")
        print(f"✅ Created: {pytest_ini}")

    print("\n✅ Test scaffolding generated!")
    print(f"   Run tests: qoo test run")


def _write_junit_xml(results: Dict, output_path: Path):
    """生成 JUnit XML 报告"""
    import xml.etree.ElementTree as ET
    from qoodev.testing import TestResult

    status_map = {
        TestResult.PASS: "passed",
        TestResult.FAIL: "failed",
        TestResult.ERROR: "error",
        TestResult.SKIP: "skipped",
    }

    testsuite = ET.Element("testsuite", {
        "name": "qoodev-skill-tests",
        "tests": str(len(results)),
        "failures": str(sum(1 for r in results.values() if r["status"] == TestResult.FAIL)),
        "errors": str(sum(1 for r in results.values() if r["status"] == TestResult.ERROR)),
    })

    for name, result in results.items():
        testcase = ET.SubElement(testsuite, "testcase", {
            "name": name,
            "time": str(result.get("duration", 0)),
        })
        if result["status"] == TestResult.FAIL:
            ET.SubElement(testcase, "failure", {
                "message": result.get("error", ""),
            }).text = result.get("traceback", "")
        elif result["status"] == TestResult.ERROR:
            ET.SubElement(testcase, "error", {
                "message": result.get("error", ""),
            })

    tree = ET.ElementTree(testsuite)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    print(f"📄 JUnit report: {output_path}")
