package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.DeviceCaConfig;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface DeviceCaConfigRepository extends JpaRepository<DeviceCaConfig, String> {

    Optional<DeviceCaConfig> findByState(String state);
}
