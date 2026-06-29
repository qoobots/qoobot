package com.qoobot.qooauth.device.repository;

import com.qoobot.qooauth.common.enums.DeviceState;
import com.qoobot.qooauth.device.entity.Device;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Spring Data JPA repository for {@link Device} entities.
 */
@Repository
public interface DeviceRepository extends JpaRepository<Device, String> {

    /**
     * Find a device by its unique factory serial number.
     */
    Optional<Device> findByDeviceSerial(String deviceSerial);

    /**
     * Find all devices bound to a specific user.
     */
    List<Device> findByBoundUserId(String boundUserId);

    /**
     * Find devices by their current state.
     */
    List<Device> findByState(DeviceState state);

    /**
     * Check whether a device serial already exists.
     */
    boolean existsByDeviceSerial(String deviceSerial);

    /**
     * Find a device by its certificate serial number.
     */
    @Query("SELECT d FROM Device d WHERE d.certificateSn = :certSn")
    Optional<Device> findByCertificateSn(@Param("certSn") String certSn);

    /**
     * Count bound devices for a user.
     */
    long countByBoundUserId(String boundUserId);

    /**
     * Find bound devices for a user that are not wiped.
     */
    @Query("SELECT d FROM Device d WHERE d.boundUserId = :userId AND d.state <> 'WIPED'")
    List<Device> findActiveByBoundUserId(@Param("userId") String userId);
}
