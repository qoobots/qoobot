package com.qoobot.qoocloud.device.service;

import com.qoobot.qoocloud.device.entity.Device;
import com.qoobot.qoocloud.device.repository.DeviceRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * DeviceGroupService — 设备分组服务
 * 按型号/版本/地域/用户分组管理设备，支持动态分组和批量操作
 */
@Service
public class DeviceGroupService {

    private static final Logger log = LoggerFactory.getLogger(DeviceGroupService.class);

    private final DeviceRepository deviceRepository;

    // 分组定义存储
    private final Map<String, DeviceGroup> groups = new ConcurrentHashMap<>();
    // 设备→分组映射
    private final Map<String, Set<String>> deviceGroupMembership = new ConcurrentHashMap<>();

    public DeviceGroupService(DeviceRepository deviceRepository) {
        this.deviceRepository = deviceRepository;
    }

    /**
     * 创建设备分组。
     */
    public DeviceGroup createGroup(String name, String description, GroupType type,
                                    Map<String, String> filters) {
        String groupId = "group_" + UUID.randomUUID().toString().substring(0, 8);

        DeviceGroup group = new DeviceGroup();
        group.groupId = groupId;
        group.name = name;
        group.description = description;
        group.type = type;
        group.filters = filters != null ? filters : Map.of();
        group.createdAt = Instant.now();
        group.updatedAt = Instant.now();

        // 自动匹配符合条件的设备
        if (type == GroupType.DYNAMIC && filters != null) {
            group.memberCount = refreshDynamicGroup(group);
        }

        groups.put(groupId, group);
        log.info("Device group created: {} ({}) — {} devices matched",
                name, groupId, group.memberCount);
        return group;
    }

    /**
     * 刷新动态分组：重新匹配设备。
     */
    public int refreshDynamicGroup(DeviceGroup group) {
        List<Device> allDevices = deviceRepository.findAll();
        int count = 0;

        for (Device device : allDevices) {
            if (matchesFilters(device, group.filters)) {
                deviceGroupMembership.computeIfAbsent(device.getDeviceId(), k -> new HashSet<>())
                        .add(group.groupId);
                count++;
            }
        }

        group.memberCount = count;
        group.updatedAt = Instant.now();
        return count;
    }

    /**
     * 手动添加设备到分组。
     */
    public void addDeviceToGroup(String groupId, String deviceId) {
        DeviceGroup group = groups.get(groupId);
        if (group == null) {
            throw new RuntimeException("Group not found: " + groupId);
        }

        Optional<Device> device = deviceRepository.findById(deviceId);
        if (device.isEmpty()) {
            throw new RuntimeException("Device not found: " + deviceId);
        }

        deviceGroupMembership.computeIfAbsent(deviceId, k -> new HashSet<>()).add(groupId);
        group.memberCount = deviceGroupMembership.values().stream()
                .filter(s -> s.contains(groupId)).count();
        group.updatedAt = Instant.now();
    }

    /**
     * 从分组中移除设备。
     */
    public void removeDeviceFromGroup(String groupId, String deviceId) {
        Set<String> memberships = deviceGroupMembership.get(deviceId);
        if (memberships != null) {
            memberships.remove(groupId);
        }

        DeviceGroup group = groups.get(groupId);
        if (group != null) {
            group.memberCount = deviceGroupMembership.values().stream()
                    .filter(s -> s.contains(groupId)).count();
            group.updatedAt = Instant.now();
        }
    }

    /**
     * 获取分组中的设备列表。
     */
    public List<Device> getGroupDevices(String groupId) {
        DeviceGroup group = groups.get(groupId);
        if (group == null) return List.of();

        return deviceGroupMembership.entrySet().stream()
                .filter(e -> e.getValue().contains(groupId))
                .map(e -> deviceRepository.findById(e.getKey()))
                .filter(Optional::isPresent)
                .map(Optional::get)
                .toList();
    }

    /**
     * 获取设备所属的所有分组。
     */
    public List<DeviceGroup> getDeviceGroups(String deviceId) {
        Set<String> groupIds = deviceGroupMembership.get(deviceId);
        if (groupIds == null) return List.of();

        return groupIds.stream()
                .map(groups::get)
                .filter(Objects::nonNull)
                .toList();
    }

    /**
     * 列出所有分组。
     */
    public List<DeviceGroup> listGroups() {
        return new ArrayList<>(groups.values());
    }

    /**
     * 获取分组详情。
     */
    public Optional<DeviceGroup> getGroup(String groupId) {
        return Optional.ofNullable(groups.get(groupId));
    }

    /**
     * 删除分组。
     */
    public void deleteGroup(String groupId) {
        groups.remove(groupId);
        deviceGroupMembership.values().forEach(s -> s.remove(groupId));
        log.info("Device group deleted: {}", groupId);
    }

    /**
     * 按分组获取设备统计。
     */
    public GroupStats getGroupStats(String groupId) {
        DeviceGroup group = groups.get(groupId);
        if (group == null) return new GroupStats(groupId, 0, 0, 0, 0);

        List<Device> devices = getGroupDevices(groupId);
        long online = devices.stream().filter(d -> "ONLINE".equals(d.getState())).count();
        long offline = devices.stream().filter(d -> "OFFLINE".equals(d.getState())).count();
        long locked = devices.stream().filter(d -> "LOCKED".equals(d.getState())).count();

        return new GroupStats(groupId, devices.size(), online, offline, locked);
    }

    /**
     * 检查设备是否匹配筛选条件。
     */
    private boolean matchesFilters(Device device, Map<String, String> filters) {
        for (Map.Entry<String, String> filter : filters.entrySet()) {
            switch (filter.getKey()) {
                case "hardwareModel":
                    if (!device.getHardwareModel().equals(filter.getValue())) return false;
                    break;
                case "firmwareVersion":
                    if (device.getFirmwareVersion() == null ||
                            !device.getFirmwareVersion().equals(filter.getValue())) return false;
                    break;
                case "state":
                    if (!device.getState().equals(filter.getValue())) return false;
                    break;
                case "region":
                    // 基于经纬度判断区域（简化实现）
                    String region = classifyRegion(device.getLastLatitude(), device.getLastLongitude());
                    if (!region.equals(filter.getValue())) return false;
                    break;
                default:
                    break;
            }
        }
        return true;
    }

    /**
     * 基于经纬度分类区域。
     */
    private String classifyRegion(Double lat, Double lng) {
        if (lat == null || lng == null) return "unknown";
        if (lat > 35 && lng > 105) return "cn-north";
        if (lat <= 35 && lng > 105) return "cn-south";
        if (lat > 30 && lng <= 105) return "cn-west";
        if (lat <= 30 && lng <= 105) return "cn-southwest";
        return "overseas";
    }

    // --- Inner Types ---

    public enum GroupType {
        STATIC,   // 手动添加/移除设备
        DYNAMIC   // 基于筛选条件自动匹配
    }

    public static class DeviceGroup {
        public String groupId;
        public String name;
        public String description;
        public GroupType type;
        public Map<String, String> filters = new HashMap<>();
        public int memberCount;
        public Instant createdAt;
        public Instant updatedAt;
    }

    public record GroupStats(
            String groupId,
            int totalDevices,
            long onlineDevices,
            long offlineDevices,
            long lockedDevices
    ) {}
}
