# qoochain — API 设计文档

> 版本：v0.1 | 最后更新：2026-06-29 | 状态：Draft | 子项目：qoochain（供应链制造）

---

## 1. BOM 管理 API

```
GET    /api/v1/bom/products                    — 产品 BOM 列表
GET    /api/v1/bom/products/{id}               — BOM 详情
POST   /api/v1/bom/products                    — 创建 BOM
PUT    /api/v1/bom/products/{id}               — 更新 BOM
GET    /api/v1/bom/products/{id}/diff?from=v1&to=v2 — BOM 版本对比
GET    /api/v1/bom/products/{id}/cost          — BOM 成本核算
POST   /api/v1/bom/products/{id}/ebom2mbom     — EBOM→MBOM 转换
```

### 1.1 BOM 结构

```json
{
  "product": "QooBot S",
  "version": "2.3",
  "bom_items": [
    {
      "level": 0,
      "part_number": "QS-ASM-001",
      "name": "头部总成",
      "quantity": 1,
      "type": "assembly",
      "children": [
        {
          "level": 1,
          "part_number": "QS-CAM-RGB-001",
          "name": "RGB相机模组",
          "quantity": 2,
          "vendor": "Sony",
          "unit_cost": 25.00,
          "lead_time_days": 30
        }
      ]
    }
  ]
}
```

---

## 2. 标定 API

```
POST   /api/v1/calibration/sessions             — 创建标定会话
POST   /api/v1/calibration/sessions/{id}/start  — 开始标定
GET    /api/v1/calibration/sessions/{id}/status  — 标定状态
POST   /api/v1/calibration/sessions/{id}/complete — 完成标定
GET    /api/v1/calibration/sessions/{id}/results — 标定结果
POST   /api/v1/calibration/sessions/{id}/retry  — 重新标定失败项
GET    /api/v1/calibration/history?sn=QS-2026-00001 — 标定历史
```

### 2.1 标定结果

```json
{
  "session_id": "CAL-20260629-0001",
  "serial_number": "QS-2026-00001",
  "status": "completed",
  "results": {
    "camera_intrinsics": {
      "left": {
        "fx": 520.9, "fy": 521.0, "cx": 325.1, "cy": 249.7,
        "distortion": [-0.283, 0.074, 0.000, 0.000],
        "reprojection_error": 0.15
      }
    },
    "imu": {
      "gyro_bias": [0.0012, -0.0008, 0.0003],
      "accel_bias": [0.012, -0.005, -0.003],
      "scale_error": 0.002
    },
    "kinematics": {
      "joint_offsets": [0.001, -0.002, 0.000, 0.001, ...],
      "link_lengths": [0.150, 0.280, 0.120, ...]
    }
  },
  "all_passed": true,
  "duration_seconds": 687
}
```

---

## 3. 质量管理 API

```
GET    /api/v1/quality/inspections             — 检验记录列表
POST   /api/v1/quality/inspections             — 创建检验记录
GET    /api/v1/quality/inspections/{id}        — 检验详情
POST   /api/v1/quality/inspections/{id}/nc    — 开不合格品报告 (NCMR)
POST   /api/v1/quality/inspections/{id}/capa  — 开纠正预防措施 (CAPA)
GET    /api/v1/quality/spc?sn=QS-2026-00001   — SPC 控制图数据
```

---

## 4. 追溯 API

```
GET    /api/v1/trace/serial/{sn}               — 按 SN 查询制造档案
GET    /api/v1/trace/lot/{lot_number}          — 按批次号查询影响范围
GET    /api/v1/trace/component/{part_number}   — 按器件号查询使用情况
GET    /api/v1/trace/passport/{sn}             — 下载数字护照 (PDF)
```

---

## 5. 供应商管理 API

```
GET    /api/v1/suppliers                        — 供应商列表
POST   /api/v1/suppliers                        — 添加供应商
PUT    /api/v1/suppliers/{id}                   — 更新供应商信息
POST   /api/v1/suppliers/{id}/audit             — 供应商审核记录
GET    /api/v1/suppliers/{id}/performance       — 供应商绩效
```

---

## 6. 错误码

| 错误码 | 描述 |
|:-------|------|
| `CHAIN_OK` (0) | 成功 |
| `CHAIN_ERR_PART_NOT_FOUND` (10001) | 物料不存在 |
| `CHAIN_ERR_CAL_FAILED` (10002) | 标定失败 |
| `CHAIN_ERR_SN_DUPLICATE` (10003) | SN 重复 |
| `CHAIN_ERR_LOT_NOT_FOUND` (10004) | 批次不存在 |
| `CHAIN_ERR_INSPECTION_FAILED` (10005) | 检验未通过 |
| `CHAIN_ERR_VENDOR_NOT_APPROVED` (10006) | 供应商未批准 |
