package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.Fido2Credential;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface Fido2CredentialRepository extends JpaRepository<Fido2Credential, String> {

    List<Fido2Credential> findByUserId(String userId);

    @Modifying
    @Query("UPDATE Fido2Credential f SET f.signCount = :signCount WHERE f.credentialId = :credentialId")
    void updateSignCount(@Param("credentialId") String credentialId, @Param("signCount") long signCount);
}
