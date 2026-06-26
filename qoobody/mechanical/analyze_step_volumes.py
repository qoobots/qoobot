#!/usr/bin/env python3
"""
分析真实的STEP文件体积，计算3D打印费用。
只处理包含 ISO-10303-21 头部的真实STEP文件（跳过Git LFS指针）。
"""
import cadquery as cq
import os
import glob
import json
import sys
from collections import defaultdict

ROOT = r"D:\05workspaces\qoobot\qoobody\mechanical\mujoco\hardware\OpenLoongHardware"

MATERIALS = [
    ("FDM/PLA",       1.25, 0.15, 0.30),
    ("SLA/树脂",      1.20, 0.50, 1.50),
    ("SLS/尼龙",      1.10, 1.00, 3.00),
    ("MJF/尼龙",      1.10, 1.50, 3.50),
    ("SLM/铝合金",    2.70, 5.00, 8.00),
    ("SLM/不锈钢",    7.85, 6.00, 10.00),
    ("SLM/钛合金",    4.51, 8.00, 15.00),
]

def categorize(filename):
    f = os.path.basename(filename).lower()
    if any(k in f for k in ["screw", "螺钉", "pin", "销", "nut", "螺母", "locking"]):
        return "紧固件(螺钉/销/螺母)"
    elif any(k in f for k in ["shaft", "轴"]):
        return "轴类零件"
    elif any(k in f for k in ["bracket", "支架", "frame", "机架"]):
        return "支架/框架"
    elif any(k in f for k in ["plate", "板", "fixing", "固定", "flange", "法兰"]):
        return "板/固定件"
    elif any(k in f for k in ["bushing", "衬套", "bearing", "轴承", "washer", "垫片", "shim", "sleeve", "套"]):
        return "轴承/衬套/垫片"
    elif any(k in f for k in ["link", "连杆", "rod", "拉杆", "arm", "臂", "crank", "曲柄"]):
        return "连杆/臂类"
    elif any(k in f for k in ["foot", "足", "sole", "底"]):
        return "腿足部件"
    elif any(k in f for k in ["motor", "电机", "adapter", "转接"]):
        return "电机/转接件"
    else:
        return "其他"

def is_real_step(filepath):
    """检查是否是真实STEP文件（非Git LFS指针）"""
    try:
        with open(filepath, 'r', errors='ignore') as f:
            first_line = f.readline().strip()
            return first_line.startswith("ISO-10303-21")
    except:
        return False

def get_step_volume(filepath):
    """读取STEP文件并返回体积(mm³)"""
    try:
        result = cq.importers.importStep(filepath)
        total_vol = 0
        solids = result.vals()
        for solid in solids:
            try:
                vol = solid.Volume()
                if vol > 0:
                    total_vol += vol
            except:
                pass
        if total_vol == 0:
            try:
                total_vol = result.val().Volume()
            except:
                pass
        return total_vol if total_vol > 0 else None
    except Exception as e:
        print(f"  ERR: {e}")
        return None

def main():
    all_steps = glob.glob(os.path.join(ROOT, "**", "*.step"), recursive=True)
    real_steps = [f for f in all_steps if is_real_step(f)]
    print(f"总STEP文件: {len(all_steps)}, 真实文件: {len(real_steps)}")

    results = []
    failed = []
    cat_volumes = defaultdict(float)
    cat_counts = defaultdict(int)
    total_volume = 0

    for i, filepath in enumerate(sorted(real_steps)):
        fname = os.path.basename(filepath)
        sys.stdout.write(f"\r[{i+1}/{len(real_steps)}] {fname[:50]}...")
        sys.stdout.flush()

        vol = get_step_volume(filepath)
        if vol is None or vol == 0:
            failed.append(fname)
            continue

        cat = categorize(filepath)
        results.append({
            "file": os.path.basename(filepath),
            "category": cat,
            "volume_mm3": round(vol, 2),
            "volume_cm3": round(vol / 1000, 2),
        })
        cat_volumes[cat] += vol
        cat_counts[cat] += 1
        total_volume += vol

    print(f"\n\n成功: {len(results)}, 失败: {len(failed)}")
    total_cm3 = total_volume / 1000

    print(f"\n{'='*70}")
    print(f"总体积统计")
    print(f"{'='*70}")
    print(f"成功分析零件数: {len(results)}")
    print(f"总体积: {total_cm3:.1f} cm³")

    print(f"\n按类别:")
    print(f"{'类别':<22} {'数量':>4} {'体积(cm³)':>10} {'占比':>6}")
    print("-" * 48)
    for cat in sorted(cat_volumes.keys(), key=lambda x: -cat_volumes[x]):
        vol_cm3 = cat_volumes[cat] / 1000
        pct = vol_cm3 / total_cm3 * 100
        print(f"{cat:<22} {cat_counts[cat]:>4} {vol_cm3:>10.1f} {pct:>5.1f}%")

    print(f"\n{'='*70}")
    print(f"3D打印费用预估")
    print(f"{'='*70}")
    print(f"{'工艺/材料':<14} {'密度':>6} {'重量(kg)':>8} {'单价(元/g)':>12} {'低价(元)':>10} {'高价(元)':>10}")
    print("-" * 70)

    cost_estimates = []
    for name, density, price_low, price_high in MATERIALS:
        mass_g = total_cm3 * density
        mass_kg = mass_g / 1000
        cost_low = mass_g * price_low
        cost_high = mass_g * price_high
        cost_estimates.append({
            "material": name,
            "density": density,
            "mass_kg": round(mass_kg, 2),
            "cost_low": round(cost_low),
            "cost_high": round(cost_high),
        })
        print(f"{name:<14} {density:>5.2f}g {mass_kg:>8.2f}  {price_low:.2f}-{price_high:.2f}      {cost_low:>10,} {cost_high:>10,}")

    out = {
        "summary": {
            "total_parts_analyzed": len(results),
            "total_volume_cm3": round(total_cm3, 1),
            "categories": {cat: {"count": cat_counts[cat], "volume_cm3": round(cat_volumes[cat]/1000, 1)} for cat in cat_volumes},
        },
        "cost_estimates": cost_estimates,
        "part_details": results,
    }
    out_path = os.path.join(os.path.dirname(__file__), "step_volume_analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {out_path}")

if __name__ == "__main__":
    main()
