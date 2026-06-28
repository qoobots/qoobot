package com.qoobot.qoogear.cert.service;

import com.qoobot.qoogear.cert.domain.Developer;
import com.qoobot.qoogear.cert.repository.DeveloperRepository;
import com.qoobot.qoogear.common.exception.QooGearException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.ZonedDateTime;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeveloperService {

    private final DeveloperRepository devRepo;

    @Transactional
    public Developer register(Developer developer) {
        if (devRepo.existsByUserId(developer.getUserId())) {
            throw QooGearException.conflict("Developer already registered");
        }
        if (devRepo.existsByContactEmail(developer.getContactEmail())) {
            throw QooGearException.conflict("Email already in use");
        }
        developer.setVerificationStatus("pending");
        return devRepo.save(developer);
    }

    public Developer getById(Long id) {
        return devRepo.findById(id)
                .orElseThrow(() -> QooGearException.notFound("Developer", id));
    }

    public Developer getByUserId(Long userId) {
        return devRepo.findByUserId(userId)
                .orElseThrow(() -> QooGearException.notFound("Developer with userId", userId));
    }

    @Transactional
    public Developer verify(Long devId, boolean approved) {
        Developer dev = getById(devId);
        dev.setVerificationStatus(approved ? "verified" : "rejected");
        if (approved) {
            dev.setVerifiedAt(ZonedDateTime.now());
        }
        log.info("Developer {} verification status: {}", dev.getCompanyName(), dev.getVerificationStatus());
        return devRepo.save(dev);
    }

    @Transactional
    public Developer updateProfile(Long devId, Developer update) {
        Developer dev = getById(devId);
        if (update.getCompanyName() != null) dev.setCompanyName(update.getCompanyName());
        if (update.getContactName() != null) dev.setContactName(update.getContactName());
        if (update.getContactPhone() != null) dev.setContactPhone(update.getContactPhone());
        if (update.getWebsite() != null) dev.setWebsite(update.getWebsite());
        if (update.getCountry() != null) dev.setCountry(update.getCountry());
        return devRepo.save(dev);
    }
}
