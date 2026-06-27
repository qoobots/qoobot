# qoodev CI 初始化命令

from pathlib import Path
from typer import Typer, Option
from typing import Optional

app = Typer(name="ci", help="CI/CD integration commands")


@app.command("init")
def init_ci(
    output_dir: str = Option("./.github/workflows", "--output", "-o", help="Output directory for workflow files"),
    include_cd: bool = Option(True, "--cd/--no-cd", help="Include CD (release) pipeline"),
):
    """Initialize CI/CD workflow files for the project"""
    import shutil

    project_root = Path.cwd()
    templates_dir = Path(__file__).parent.parent.parent.parent / ".github" / "workflows"

    output_path = project_root / output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    # 复制 CI 模板
    ci_template = templates_dir / "ci.yml"
    if ci_template.exists():
        shutil.copy(ci_template, output_path / "ci.yml")
        print(f"✅ CI workflow: {output_path / 'ci.yml'}")
    else:
        _write_ci_template(output_path / "ci.yml")
        print(f"✅ CI workflow: {output_path / 'ci.yml'}")

    # 复制 CD 模板
    if include_cd:
        cd_template = templates_dir / "cd.yml"
        if cd_template.exists():
            shutil.copy(cd_template, output_path / "cd.yml")
            print(f"✅ CD workflow: {output_path / 'cd.yml'}")
        else:
            _write_cd_template(output_path / "cd.yml")
            print(f"✅ CD workflow: {output_path / 'cd.yml'}")

    print("\n✅ CI/CD initialized!")
    print("   Next steps:")
    print("   1. Review and customize .github/workflows/ci.yml")
    print("   2. Add secrets in GitHub Settings > Secrets:")
    print("      - QOO_SIGNING_KEY (for code signing)")
    print("      - QOOECO_API_KEY (for market publishing)")


def _write_ci_template(path: Path):
    """写入 CI 模板 (内置备份)"""
    path.write_text("""\
name: qoodev CI
on: [push, pull_request, workflow_dispatch]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.10" }
      - run: pip install ruff && ruff check .
  test:
    runs-on: ubuntu-latest
    needs: [lint]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.10" }
      - run: pip install -e ".[dev]" && qoo test run
  package:
    runs-on: ubuntu-latest
    needs: [test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.10" }
      - run: pip install -e "." && qoo package build
""", encoding="utf-8")


def _write_cd_template(path: Path):
    """写入 CD 模板 (内置备份)"""
    path.write_text("""\
name: qoodev CD
on:
  push:
    tags: ["v*"]
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.10" }
      - run: pip install -e "." && qoo package build
      - uses: softprops/action-gh-release@v2
        with:
          files: dist/*.qooskills
          generate_release_notes: true
""", encoding="utf-8")
