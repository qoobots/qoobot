package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.OAuth2AuthorizationCode;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface OAuth2AuthorizationCodeRepository extends JpaRepository<OAuth2AuthorizationCode, String> {

    Optional<OAuth2AuthorizationCode> findByCodeAndUsedFalse(String code);
}
