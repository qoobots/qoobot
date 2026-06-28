package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.IpReputation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface IpReputationRepository extends JpaRepository<IpReputation, String> {

    Optional<IpReputation> findByIpAddress(String ipAddress);

    boolean existsByIpAddressAndBlocked(String ipAddress, boolean blocked);
}
