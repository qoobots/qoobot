package com.qoobot.qoocommunity.academy.repository;

import com.qoobot.qoocommunity.academy.domain.UserCertification;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface UserCertificationRepository extends JpaRepository<UserCertification, Long> {
    List<UserCertification> findByUserId(String userId);
}
