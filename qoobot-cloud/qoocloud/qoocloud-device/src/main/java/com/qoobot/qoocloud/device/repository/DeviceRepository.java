package com.qoobot.qoocloud.device.repository;

import com.qoobot.qoocloud.device.entity.Device;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;

@Repository
public interface DeviceRepository extends JpaRepository<Device, String> {

    List<Device> findByBoundUserId(String boundUserId);

    List<Device> findByState(String state);

    long countByState(String state);

    List<Device> findByStateAndLastSeenAtBefore(String state, Instant lastSeenAt);
}
