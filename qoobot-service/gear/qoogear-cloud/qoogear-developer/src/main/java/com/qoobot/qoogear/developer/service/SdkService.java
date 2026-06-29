package com.qoobot.qoogear.developer.service;

import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.developer.domain.SdkRelease;
import com.qoobot.qoogear.developer.repository.SdkReleaseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.ZonedDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class SdkService {

    private final SdkReleaseRepository sdkRepo;

    public List<SdkRelease> listReleases(String platform) {
        return sdkRepo.findByPlatform(platform);
    }

    public SdkRelease getLatest(String platform) {
        return sdkRepo.findByPlatformAndIsLatestTrue(platform)
                .orElseThrow(() -> QooGearException.notFound("SDK for platform", platform));
    }

    public SdkRelease getRelease(Long id) {
        return sdkRepo.findById(id)
                .orElseThrow(() -> QooGearException.notFound("SdkRelease", id));
    }

    @Transactional
    public SdkRelease publishRelease(SdkRelease release) {
        release.setReleasedAt(ZonedDateTime.now());
        if (Boolean.TRUE.equals(release.getIsLatest())) {
            sdkRepo.resetLatestForPlatform(release.getPlatform());
        }
        return sdkRepo.save(release);
    }

    @Transactional
    public SdkRelease setAsLatest(Long id) {
        SdkRelease release = getRelease(id);
        sdkRepo.resetLatestForPlatform(release.getPlatform());
        release.setIsLatest(true);
        return sdkRepo.save(release);
    }
}
