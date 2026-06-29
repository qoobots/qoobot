package com.qoobot.qooauth.apikey.repository;

import com.qoobot.qooauth.apikey.entity.ApiKey;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ApiKeyRepository extends JpaRepository<ApiKey, String> {

    List<ApiKey> findByUserId(String userId);

    Optional<ApiKey> findByKeyPrefix(String keyPrefix);

    List<ApiKey> findByState(String state);

    List<ApiKey> findByUserIdAndState(String userId, String state);

    long countByUserIdAndState(String userId, String state);
}
