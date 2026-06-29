package com.qoobot.qoogear.lab.service;

import com.qoobot.qoogear.common.dto.PageResponse;
import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.lab.domain.*;
import com.qoobot.qoogear.lab.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.ZonedDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class LaboratoryService {

    private final LaboratoryRepository labRepo;
    private final LabEquipmentRepository equipmentRepo;

    public List<Laboratory> listActive() {
        return labRepo.findByStatus("active");
    }

    public List<Laboratory> listByCountry(String country) {
        return labRepo.findByCountry(country);
    }

    public Laboratory getLab(Long id) {
        return labRepo.findById(id)
                .orElseThrow(() -> QooGearException.notFound("Laboratory", id));
    }

    @Transactional
    public Laboratory registerLab(Laboratory lab) {
        return labRepo.save(lab);
    }

    @Transactional
    public Laboratory updateStatus(Long id, String status) {
        Laboratory lab = getLab(id);
        lab.setStatus(status);
        return labRepo.save(lab);
    }

    // === Equipment Management ===

    public List<LabEquipment> getEquipment(Long labId) {
        return equipmentRepo.findByLaboratoryId(labId);
    }

    @Transactional
    public LabEquipment addEquipment(LabEquipment equipment) {
        return equipmentRepo.save(equipment);
    }

    @Transactional
    public LabEquipment calibrateEquipment(Long equipmentId) {
        LabEquipment eq = equipmentRepo.findById(equipmentId)
                .orElseThrow(() -> QooGearException.notFound("LabEquipment", equipmentId));
        eq.setCalibratedAt(ZonedDateTime.now());
        eq.setNextCalibrationDue(ZonedDateTime.now().plusMonths(12));
        return equipmentRepo.save(eq);
    }

    public List<LabEquipment> findNeedingCalibration(int daysAhead) {
        return equipmentRepo.findNeedingCalibration(ZonedDateTime.now().plusDays(daysAhead));
    }
}
