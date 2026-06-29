package com.qoobot.qoostore.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class StorageService {

    // In production: upload to MinIO/S3
    // For development: return placeholder URLs

    public String uploadPackage(String skillId, String version, MultipartFile file) {
        String objectKey = String.format("qoostore/packages/%s/%s/skill-%s.qooskills",
                skillId, version, version);
        log.info("Package uploaded: skillId={}, version={}, key={}, size={}",
                skillId, version, objectKey, file.getSize());
        return "s3://qoostore/" + objectKey;
    }

    public String uploadIcon(String skillId, MultipartFile file) {
        String objectKey = String.format("qoostore/icons/%s/icon_512.png", skillId);
        log.info("Icon uploaded: skillId={}, key={}", skillId, objectKey);
        return "s3://qoostore/" + objectKey;
    }

    public String uploadScreenshot(String skillId, int index, MultipartFile file) {
        String objectKey = String.format("qoostore/screenshots/%s/screenshot_%d.png", skillId, index);
        log.info("Screenshot uploaded: skillId={}, index={}, key={}", skillId, index, objectKey);
        return "s3://qoostore/" + objectKey;
    }

    public void deletePackage(String skillId, String version) {
        String objectKey = String.format("qoostore/packages/%s/%s/skill-%s.qooskills",
                skillId, version, version);
        log.info("Package deleted: skillId={}, version={}, key={}", skillId, version, objectKey);
    }
}
