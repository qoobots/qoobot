#!/usr/bin/env python3
"""
基于已分析的腿足系统STEP体积数据，推算全机器人3D打印费用。

已知数据:
  - 腿足系统(单腿) 36个零件, 总体积 1937.3 cm³
  - 原始设计重量 80kg, 用户预估3D打印版 ~100kg
  - 各子系统零件数: 腰部9, 胸腔16+, 头部13, 腿足42(单腿)

推算方法:
  1. 腿足系统按实测体积×2(双腿)
  2. 腰部/胸腔/头部按零件数和典型体积比推算
  3. 标注推算部分的不确定性
"""
import json

# === 实测数据 (单腿, 36零件) ===
LEG_VOLUME_CM3 = 1937.3  # cm³, 实测
LEG_PART_COUNT = 36

# 需要镜像的右侧零件 (从文件名识别)
BILATERAL_PARTS = [
    "右大腿支架",      # TA00-12-02-0003
    "右小腿支架",      # TA00-12-04-0001
    "右小腿下限位",    # TA00-12-04-0005
    "右小腿上限位",    # TA00-12-04-0006
]

# === 各子系统推算 ===
# 腿足系统: 双腿 = 1937.3 × 2 = 3874.6 cm³
#   (其中4个右侧零件需要镜像, 但体积相同)
leg_both = LEG_VOLUME_CM3 * 2

# 腰部组件 (9个零件: 支架×4, 轴×2, 销×2, 固定片×1)
# 典型腰部零件平均体积 ~150-250 cm³
waist_est_low = 9 * 100   # 保守
waist_est_high = 9 * 250  # 乐观
waist_est_mid = (waist_est_low + waist_est_high) / 2

# 胸腔系统 (16个零件: 前胸机架, 吊环, 固定板等)
# 前胸机架是最大件, 类似大腿支架量级
chest_est_low = 16 * 80
chest_est_high = 16 * 200
chest_est_mid = (chest_est_low + chest_est_high) / 2

# 头部感知系统 (13个零件: 框架板, 支撑, 相机支架等)
# 头部零件偏小
head_est_low = 13 * 40
head_est_high = 13 * 120
head_est_mid = (head_est_low + head_est_high) / 2

# === 全机器人总计 ===
total_low = leg_both + waist_est_low + chest_est_low + head_est_low
total_mid = leg_both + waist_est_mid + chest_est_mid + head_est_mid
total_high = leg_both + waist_est_high + chest_est_high + head_est_high

print("=" * 70)
print("青龙人形机器人 - 3D打印费用预估")
print("=" * 70)

print(f"\n{'子系统':<20} {'零件数':>6} {'体积(cm³)':>16} {'数据来源':>10}")
print("-" * 60)
print(f"{'腿足系统(双腿)':<18} {42*2:>6} {leg_both:>16.1f} {'实测×2':>10}")
print(f"{'腰部组件':<18} {9:>6} {waist_est_mid:>16.1f} {'推算':>10}")
print(f"{'胸腔系统':<18} {16:>6} {chest_est_mid:>16.1f} {'推算':>10}")
print(f"{'头部感知系统':<18} {13:>6} {head_est_mid:>16.1f} {'推算':>10}")
print("-" * 60)
print(f"{'合计(中值)':<18} {84:>6} {total_mid:>16.1f}")
print(f"{'合计(低值)':<18} {'':>6} {total_low:>16.1f}")
print(f"{'合计(高值)':<18} {'':>6} {total_high:>16.1f}")

# === 材料与工艺费用 ===
MATERIALS = [
    ("FDM/PLA",       1.25, 0.15, 0.30, "原型验证, 非承力"),
    ("SLA/树脂",      1.20, 0.50, 1.50, "高精度, 外壳件"),
    ("SLS/尼龙",      1.10, 1.00, 3.00, "韧性件, 功能测试"),
    ("MJF/尼龙",      1.10, 1.50, 3.50, "高强度, 最终件"),
    ("SLM/铝合金",    2.70, 5.00, 8.00, "金属结构件"),
    ("SLM/不锈钢",    7.85, 6.00, 10.00, "高强金属件"),
    ("SLM/钛合金",    4.51, 8.00, 15.00, "航空级, 最轻最强"),
]

print(f"\n{'='*70}")
print(f"全机器人3D打印费用预估 (基于中值体积 {total_mid:.0f} cm³)")
print(f"{'='*70}")
print(f"{'工艺/材料':<14} {'密度':>5} {'重量(kg)':>8} {'单价(元/g)':>12} {'费用范围(元)':>16} {'适用场景':>16}")
print("-" * 80)

for name, density, price_low, price_high, scenario in MATERIALS:
    mass_g = total_mid * density
    mass_kg = mass_g / 1000
    cost_low = mass_g * price_low
    cost_high = mass_g * price_high
    print(f"{name:<14} {density:>4.2f}g {mass_kg:>8.2f}  {price_low:.2f}-{price_high:.2f}      {cost_low:>8,.0f}-{cost_high:<8,.0f}   {scenario}")

# === 混合方案 (推荐) ===
print(f"\n{'='*70}")
print(f"推荐混合方案 (不同零件用不同工艺)")
print(f"{'='*70}")

scenarios = [
    ("方案A: 全树脂验证件", [
        ("SLA/树脂", total_mid, 0.80),
    ]),
    ("方案B: 树脂+尼龙混合", [
        ("SLA/树脂", total_mid * 0.6, 0.80),
        ("SLS/尼龙", total_mid * 0.4, 2.00),
    ]),
    ("方案C: 尼龙+铝合金", [
        ("SLS/尼龙", total_mid * 0.5, 2.00),
        ("SLM/铝合金", total_mid * 0.5, 6.50),
    ]),
    ("方案D: 全铝合金", [
        ("SLM/铝合金", total_mid, 6.50),
    ]),
]

DENSITY = {"SLA/树脂": 1.20, "SLS/尼龙": 1.10, "SLM/铝合金": 2.70}
LABELS = {"SLA/树脂": "树脂(外壳/支架)", "SLS/尼龙": "尼龙(受力件)", "SLM/铝合金": "铝合金(结构件)"}

for name, parts in scenarios:
    total_cost = 0
    total_mass = 0
    details = []
    for mat, vol, price in parts:
        mass = vol * DENSITY[mat]
        cost = mass * price
        total_cost += cost
        total_mass += mass
        details.append(f"{LABELS[mat]} {mass/1000:.1f}kg/{cost:,.0f}元")
    print(f"\n  {name}")
    print(f"    {' + '.join(details)}")
    print(f"    总重: {total_mass/1000:.1f}kg  总费用: {total_cost:,.0f}元")

# === 注意事项 ===
print(f"\n{'='*70}")
print(f"重要说明")
print(f"{'='*70}")
print(f"""
1. 体积数据来源: 腿足系统36个零件为STEP文件实测, 其余系统按零件数推算
2. V2.5版本的190个STEP文件因Git LFS未拉取, 无法直接分析(体积可能不同)
3. 费用仅含3D打印材料费, 不含:
   - 后处理(打磨/喷砂/染色/喷漆): +10-30%
   - 电机/传感器/紧固件等BOM: 另计
   - 装配与调试人工: 另计
   - 运费: 通常50-200元
4. 实际报价以上传文件后服务商自动报价为准
5. 原始机器人重80kg(含电机/电子件), 3D打印结构件重量远小于此
""")
