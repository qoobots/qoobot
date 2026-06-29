package com.qoobot.qooauth.security.repository;

import com.qoobot.qooauth.security.entity.PrivacyLabel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * Repository for PrivacyLabel entity.
 */
@Repository
public interface PrivacyLabelRepository extends JpaRepository<PrivacyLabel, Long> {

    /**
     * Find privacy labels by category.
     */
    List<PrivacyLabel> findByLabelCategory(String labelCategory);
}
