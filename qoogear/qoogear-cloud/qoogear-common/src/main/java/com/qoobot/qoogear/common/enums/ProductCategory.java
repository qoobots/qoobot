package com.qoobot.qoogear.common.enums;

public enum ProductCategory {
    GRIPPER("末端执行器"),
    SENSOR("传感器模组"),
    WEARABLE("可穿戴外设"),
    POWER("电源与充电配件"),
    MOBILITY("移动平台配件"),
    TOOL("专用工具");

    private final String displayName;

    ProductCategory(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() { return displayName; }
}
