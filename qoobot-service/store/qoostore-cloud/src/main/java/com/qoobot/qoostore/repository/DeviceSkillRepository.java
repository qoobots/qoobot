package com.qoobot.qoostore.repository;

import com.qoobot.qoostore.entity.DeviceSkill;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface DeviceSkillRepository extends JpaRepository<DeviceSkill, Long> {
    List<DeviceSkill> findByDeviceId(String deviceId);
    Optional<DeviceSkill> findByDeviceIdAndSkillId(String deviceId, Long skillId);
    List<DeviceSkill> findByDeviceIdAndStatus(String deviceId, String status);
}
