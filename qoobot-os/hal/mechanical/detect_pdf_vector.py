#!/usr/bin/env python3
"""
检测 PDF 是否为矢量图（工程图）还是扫描件（光栅图）。

判断逻辑：
  - vector_paths: 页面中的矢量绘图命令数（线段、圆弧、贝塞尔等）
  - raster_images: 页面中嵌入的位图数量
  - text_blocks: 文字块数量（尺寸标注、标题栏等）

分类规则：
  - VECTOR:   vector_paths > 50 且 raster_images == 0  → 纯矢量工程图，可转 DXF
  - MIXED:    vector_paths > 50 且 raster_images > 0    → 矢量+位图混合
  - RASTER:   vector_paths <= 10 且 raster_images > 0   → 扫描件，只能 OCR
"""

import fitz  # pymupdf
import os
import glob
import json
from collections import defaultdict

ROOT = r"D:\05workspaces\qoobot\qoobody\mechanical\mujoco\hardware\OpenLoongHardware"


def analyze_pdf(filepath):
    """分析单个 PDF，返回矢量/光栅信息。"""
    try:
        doc = fitz.open(filepath)
    except Exception as e:
        return {"error": str(e)}

    total_vector = 0
    total_raster = 0
    total_text = 0
    page_count = len(doc)

    for page in doc:
        # 矢量路径数
        try:
            drawings = page.get_drawings()
            total_vector += len(drawings)
        except Exception:
            pass

        # 位图数
        try:
            images = page.get_images(full=True)
            total_raster += len(images)
        except Exception:
            pass

        # 文字块数
        try:
            text = page.get_text("blocks")
            total_text += len(text)
        except Exception:
            pass

    doc.close()

    # 分类
    if total_vector > 50 and total_raster == 0:
        category = "VECTOR"
    elif total_vector > 50 and total_raster > 0:
        category = "MIXED"
    elif total_vector <= 10 and total_raster > 0:
        category = "RASTER"
    elif total_vector > 10:
        category = "VECTOR_LITE"
    else:
        category = "EMPTY"

    return {
        "pages": page_count,
        "vector_paths": total_vector,
        "raster_images": total_raster,
        "text_blocks": total_text,
        "category": category,
    }


def main():
    # 收集所有 PDF
    pdfs = []
    for ext in ("*.pdf", "*.PDF"):
        pdfs.extend(glob.glob(os.path.join(ROOT, "**", ext), recursive=True))

    pdfs = sorted(set(pdfs))
    print(f"找到 {len(pdfs)} 个 PDF 文件\n")
    print(f"{'分类':<14} {'页数':>4} {'矢量路径':>8} {'位图':>4} {'文字块':>6}  文件名")
    print("-" * 110)

    results = []
    category_counts = defaultdict(int)

    for pdf in pdfs:
        info = analyze_pdf(pdf)
        info["file"] = os.path.relpath(pdf, ROOT)
        results.append(info)
        category_counts[info.get("category", "ERROR")] += 1

        fname = os.path.basename(pdf)
        if "error" in info:
            print(f"{'ERROR':<14} {'-':>4} {'-':>8} {'-':>4} {'-':>6}  {fname}")
        else:
            print(
                f"{info['category']:<14} {info['pages']:>4} "
                f"{info['vector_paths']:>8} {info['raster_images']:>4} "
                f"{info['text_blocks']:>6}  {fname}"
            )

    print("\n" + "=" * 60)
    print("汇总统计")
    print("=" * 60)
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat:<14}: {count} 个")
    print(f"  {'总计':<14}: {len(pdfs)} 个")

    # 输出 JSON 供后续使用
    out_path = os.path.join(os.path.dirname(__file__), "pdf_vector_detection.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {out_path}")


if __name__ == "__main__":
    main()
