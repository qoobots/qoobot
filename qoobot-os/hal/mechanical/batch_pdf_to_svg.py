#!/usr/bin/env python3
"""
批量将 PDF 工程图转换为 SVG（用于网站矢量展示）
输出目录结构镜像原始目录，方便网站引用
"""

import fitz
import os
import time
import sys
from pathlib import Path

SRC_ROOT = r"D:\05workspaces\qoobot\qoobody\mechanical\mujoco\hardware\OpenLoongHardware"
DST_ROOT = r"D:\05workspaces\qoobot\qoobody\mechanical\web_preview\svg"

def sanitize_filename(name: str) -> str:
    """保留中文，仅替换文件系统非法字符"""
    illegal = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for ch in illegal:
        name = name.replace(ch, '_')
    return name

def pdf_to_svg(pdf_path: str, svg_path: str) -> tuple:
    """
    将单个 PDF 页面转换为 SVG
    返回 (success: bool, svg_size: int, page_count: int, error: str)
    """
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        # 工程图通常只有1页，多页取第一页
        page = doc[0]
        svg_data = page.get_svg_image()

        os.makedirs(os.path.dirname(svg_path), exist_ok=True)
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg_data)

        svg_size = os.path.getsize(svg_path)
        doc.close()
        return True, svg_size, page_count, None
    except Exception as e:
        return False, 0, 0, str(e)

def main():
    t0 = time.time()
    pdf_files = []

    # 收集所有 PDF 文件
    for root, dirs, files in os.walk(SRC_ROOT):
        for f in files:
            if f.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, f))

    total = len(pdf_files)
    print(f"找到 {total} 个 PDF 文件，开始转换...")

    success = 0
    failed = 0
    skipped = 0
    total_svg_size = 0
    errors = []
    size_bins = {"<100KB": 0, "100KB-500KB": 0, "500KB-1MB": 0, ">1MB": 0}

    for i, pdf_path in enumerate(pdf_files):
        # 计算相对路径，保持目录镜像
        rel_path = os.path.relpath(pdf_path, SRC_ROOT)
        # 替换扩展名为 .svg
        rel_svg = Path(rel_path).with_suffix('.svg')
        svg_path = os.path.join(DST_ROOT, rel_svg)

        # 如果已存在且大小合理，跳过
        if os.path.exists(svg_path) and os.path.getsize(svg_path) > 1024:
            skipped += 1
            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{total}] 跳过已存在: {os.path.basename(pdf_path)}")
            continue

        ok, svg_size, page_count, err = pdf_to_svg(pdf_path, svg_path)

        if ok:
            success += 1
            total_svg_size += svg_size
            # 分类统计
            sz_kb = svg_size / 1024
            if sz_kb < 100:
                size_bins["<100KB"] += 1
            elif sz_kb < 500:
                size_bins["100KB-500KB"] += 1
            elif sz_kb < 1024:
                size_bins["500KB-1MB"] += 1
            else:
                size_bins[">1MB"] += 1
        else:
            failed += 1
            errors.append((pdf_path, err))

        if (i + 1) % 20 == 0 or (i + 1) == total:
            elapsed = time.time() - t0
            avg = elapsed / max(i + 1 - skipped, 1)
            eta = avg * (total - i - 1)
            print(f"  [{i+1}/{total}] 成功:{success} 失败:{failed} 跳过:{skipped} | SVG总量:{total_svg_size/1024/1024:.1f}MB | ETA:{eta:.0f}s")

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"转换完成！耗时: {elapsed:.1f}s")
    print(f"  成功: {success}")
    print(f"  失败: {failed}")
    print(f"  跳过: {skipped}")
    print(f"  SVG 总大小: {total_svg_size/1024/1024:.1f} MB")
    print(f"  平均大小: {total_svg_size/success/1024:.1f} KB" if success else "")
    print(f"\nSVG 大小分布:")
    for k, v in size_bins.items():
        print(f"  {k}: {v} 个 ({v/total*100:.1f}%)")
    if errors:
        print(f"\n失败文件:")
        for pdf, err in errors[:10]:
            print(f"  {os.path.basename(pdf)}: {err}")

if __name__ == "__main__":
    main()
