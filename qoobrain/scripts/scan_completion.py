"""
scan_completion.py
扫描 Brain OS monorepo 各子项目的文件完成状态，输出报告。
"""
import os
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
MODULES = [
    "brain_core",
    "brain_ai",
    "brain_viz",
    "brain_sdk",
    "brain_proto",
    "brain_sim",
    "brain_models",
    "brain_deploy",
    "brain_docs",
]

# 扫描时跳过的目录/文件
SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".next", "dist", "build",
    "proto_gen", ".workbuddy", "coverage", ".pytest_cache",
}
SKIP_EXTS = {".pyc", ".pyo", ".lock", ".sum"}
# 这些扩展名的文件即使有内容也不算"真正有代码"（纯标记文件）
MARKER_EXTS = {".gitkeep", ".gitignore", ".gitattributes"}


def scan_file(path: Path) -> dict:
    """返回单个文件的分析结果"""
    size = path.stat().st_size
    ext = path.suffix.lower()
    is_marker = ext in MARKER_EXTS or path.name.startswith(".")

    if size == 0:
        status = "empty"
    elif is_marker:
        status = "marker"  # .gitkeep 等
    else:
        # 读取前 30 行判断是否只是骨架
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            lines = []
        non_blank = [l for l in lines if l.strip()]
        comment_like = [l for l in non_blank if l.strip().startswith(("#", "//", "/*", "*", "<!--", "---", "syntax ="))]
        if len(non_blank) == 0:
            status = "empty"
        elif len(non_blank) <= 5 and len(non_blank) == len(comment_like):
            status = "stub_only"  # 只有注释/shebang
        elif "TODO" in path.read_text(encoding="utf-8", errors="ignore")[:3000] or "pass" in path.read_text(encoding="utf-8", errors="ignore")[:3000]:
            status = "partial"  # 有 TODO 或 pass
        else:
            status = "done"

    return {
        "file": str(path.relative_to(ROOT)),
        "size": size,
        "status": status,
        "lines": sum(1 for _ in open(path, encoding="utf-8", errors="ignore")) if size > 0 else 0,
    }


def scan_module(module: str) -> dict:
    mod_path = ROOT / module
    if not mod_path.exists():
        return {"module": module, "exists": False, "files": [], "summary": {}}

    files = []
    for root, dirs, filenames in os.walk(mod_path):
        # 过滤跳过目录
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in filenames:
            fpath = Path(root) / fname
            ext = fpath.suffix.lower()
            if ext in SKIP_EXTS:
                continue
            files.append(scan_file(fpath))

    summary = {"total": len(files), "empty": 0, "stub_only": 0, "partial": 0, "done": 0, "marker": 0}
    for f in files:
        summary[f["status"]] = summary.get(f["status"], 0) + 1

    # 计算完成度（marker 不计入）
    code_files = summary["total"] - summary["marker"]
    complete_files = summary["done"]
    partial_files = summary["partial"]
    completion_pct = int((complete_files + partial_files * 0.5) / max(code_files, 1) * 100)

    return {
        "module": module,
        "exists": True,
        "files": files,
        "summary": summary,
        "code_files": code_files,
        "completion_pct": completion_pct,
    }


def main():
    results = []
    for mod in MODULES:
        r = scan_module(mod)
        results.append(r)

    # 打印报告
    print("=" * 70)
    print("Brain OS 各模块文件完成状态扫描报告")
    print("=" * 70)

    STATUS_LABEL = {
        "empty": "空文件",
        "stub_only": "仅骨架",
        "partial": "部分完成(含TODO/pass)",
        "done": "完成",
        "marker": "标记文件",
    }

    for r in results:
        mod = r["module"]
        if not r["exists"]:
            print(f"\n[{mod}] ⚠️  目录不存在")
            continue

        s = r["summary"]
        pct = r["completion_pct"]
        icon = "✅" if pct >= 80 else ("🔶" if pct >= 40 else "❌")
        print(f"\n[{mod}]  {icon}  完成度 {pct}%  (代码文件 {r['code_files']} 个)")
        print(f"  总文件: {s['total']}  |  "
              f"空: {s['empty']}  |  "
              f"仅骨架: {s['stub_only']}  |  "
              f"含TODO/pass: {s['partial']}  |  "
              f"完成: {s['done']}  |  "
              f"标记: {s['marker']}")

        # 打印空文件和仅骨架文件列表
        problem_files = [f for f in r["files"] if f["status"] in ("empty", "stub_only")]
        if problem_files:
            print(f"  --- 问题文件（空/仅骨架）[{len(problem_files)} 个] ---")
            for f in problem_files[:30]:  # 最多显示30个
                print(f"    [{f['status']:10s}] {f['file']}")
            if len(problem_files) > 30:
                print(f"    ... 还有 {len(problem_files) - 30} 个")

    print("\n" + "=" * 70)
    print("汇总")
    print("=" * 70)
    for r in results:
        if not r["exists"]:
            continue
        pct = r["completion_pct"]
        icon = "✅" if pct >= 80 else ("🔶" if pct >= 40 else "❌")
        print(f"  {icon}  {r['module']:20s}  {pct:3d}%  "
              f"(空:{r['summary']['empty']}  骨架:{r['summary']['stub_only']}  部分:{r['summary']['partial']}  完成:{r['summary']['done']})")

    # 保存 JSON
    out = ROOT / "scripts" / "scan_result.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存至: {out}")


if __name__ == "__main__":
    main()
