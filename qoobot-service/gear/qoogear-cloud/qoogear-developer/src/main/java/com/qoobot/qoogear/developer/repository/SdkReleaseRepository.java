package com.qoobot.qoogear.developer.repository;

import com.qoobot.qoogear.developer.domain.SdkRelease;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface SdkReleaseRepository extends JpaRepository<SdkRelease, Long> {
    List<SdkRelease> findByPlatform(String platform);
    Optional<SdkRelease> findByPlatformAndVersion(String platform, String version);
    Optional<SdkRelease> findByPlatformAndIsLatestTrue(String platform);

    @Modifying
    @Query("UPDATE SdkRelease s SET s.isLatest = false WHERE s.platform = :platform")
    void resetLatestForPlatform(@Param("platform") String platform);
}
