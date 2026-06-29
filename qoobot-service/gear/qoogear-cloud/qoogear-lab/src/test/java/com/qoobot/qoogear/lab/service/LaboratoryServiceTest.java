package com.qoobot.qoogear.lab.service;

import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.lab.domain.LabEquipment;
import com.qoobot.qoogear.lab.domain.Laboratory;
import com.qoobot.qoogear.lab.repository.LabEquipmentRepository;
import com.qoobot.qoogear.lab.repository.LaboratoryRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.ZonedDateTime;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit tests for LaboratoryService.
 */
@ExtendWith(MockitoExtension.class)
class LaboratoryServiceTest {

    @Mock private LaboratoryRepository labRepo;
    @Mock private LabEquipmentRepository equipmentRepo;

    @InjectMocks
    private LaboratoryService service;

    private Laboratory lab;
    private LabEquipment equipment;

    @BeforeEach
    void setUp() {
        lab = new Laboratory();
        lab.setId(1L);
        lab.setName("深圳机器人测试中心");
        lab.setLabCode("LAB-CN-001");
        lab.setCountry("CN");
        lab.setCity("深圳");
        lab.setAddress("广东省深圳市南山区科技园路1号");
        lab.setContactName("张三");
        lab.setContactEmail("zhangsan@lab-cn-001.com");
        lab.setContactPhone("+86-755-88888888");
        lab.setAccreditation("CNAS L0001");
        lab.setScope(List.of("gripper", "sensor", "wearable"));
        lab.setStatus("active");

        equipment = new LabEquipment();
        equipment.setId(1L);
        equipment.setLaboratoryId(1L);
        equipment.setName("高精度力传感器测试台");
        equipment.setModel("FT-5000");
        equipment.setSerialNumber("FT2026-001");
        equipment.setEquipmentType("force_sensor");
        equipment.setCalibratedAt(ZonedDateTime.now().minusMonths(3));
        equipment.setNextCalibrationDue(ZonedDateTime.now().plusMonths(9));
        equipment.setStatus("active");
    }

    // === Laboratory Tests ===

    @Test
    void shouldListActiveLabs() {
        when(labRepo.findByStatus("active")).thenReturn(List.of(lab));
        List<Laboratory> result = service.listActive();
        assertEquals(1, result.size());
        assertEquals("active", result.get(0).getStatus());
    }

    @Test
    void shouldListLabsByCountry() {
        when(labRepo.findByCountry("CN")).thenReturn(List.of(lab));
        List<Laboratory> result = service.listByCountry("CN");
        assertEquals(1, result.size());
        assertEquals("CN", result.get(0).getCountry());
    }

    @Test
    void shouldGetLabById() {
        when(labRepo.findById(1L)).thenReturn(Optional.of(lab));
        Laboratory result = service.getLab(1L);
        assertNotNull(result);
        assertEquals("LAB-CN-001", result.getLabCode());
    }

    @Test
    void shouldThrowWhenLabNotFound() {
        when(labRepo.findById(999L)).thenReturn(Optional.empty());
        assertThrows(QooGearException.class, () -> service.getLab(999L));
    }

    @Test
    void shouldRegisterLab() {
        when(labRepo.save(any(Laboratory.class))).thenReturn(lab);
        Laboratory result = service.registerLab(lab);
        assertNotNull(result);
        assertEquals("深圳机器人测试中心", result.getName());
    }

    @Test
    void shouldUpdateLabStatus() {
        when(labRepo.findById(1L)).thenReturn(Optional.of(lab));
        when(labRepo.save(any(Laboratory.class))).thenReturn(lab);

        Laboratory result = service.updateStatus(1L, "suspended");
        assertEquals("suspended", result.getStatus());
    }

    @Test
    void shouldUpdateLabStatusToCertified() {
        when(labRepo.findById(1L)).thenReturn(Optional.of(lab));
        when(labRepo.save(any(Laboratory.class))).thenReturn(lab);

        Laboratory result = service.updateStatus(1L, "certified");
        assertEquals("certified", result.getStatus());
    }

    // === Equipment Tests ===

    @Test
    void shouldGetEquipmentByLabId() {
        when(equipmentRepo.findByLaboratoryId(1L)).thenReturn(List.of(equipment));
        List<LabEquipment> result = service.getEquipment(1L);
        assertEquals(1, result.size());
        assertEquals("FT-5000", result.get(0).getModel());
    }

    @Test
    void shouldAddEquipment() {
        when(equipmentRepo.save(any(LabEquipment.class))).thenReturn(equipment);
        LabEquipment result = service.addEquipment(equipment);
        assertNotNull(result);
        assertEquals("高精度力传感器测试台", result.getName());
    }

    @Test
    void shouldCalibrateEquipment() {
        when(equipmentRepo.findById(1L)).thenReturn(Optional.of(equipment));
        when(equipmentRepo.save(any(LabEquipment.class))).thenReturn(equipment);

        LabEquipment result = service.calibrateEquipment(1L);
        assertNotNull(result.getCalibratedAt());
        assertNotNull(result.getNextCalibrationDue());
        // Next calibration should be ~12 months from now
        assertTrue(result.getNextCalibrationDue().isAfter(result.getCalibratedAt()));
    }

    @Test
    void shouldThrowWhenEquipmentNotFoundForCalibration() {
        when(equipmentRepo.findById(999L)).thenReturn(Optional.empty());
        assertThrows(QooGearException.class, () -> service.calibrateEquipment(999L));
    }

    @Test
    void shouldFindEquipmentNeedingCalibration() {
        ZonedDateTime threshold = ZonedDateTime.now().plusDays(30);
        when(equipmentRepo.findNeedingCalibration(any(ZonedDateTime.class)))
                .thenReturn(List.of(equipment));

        List<LabEquipment> result = service.findNeedingCalibration(30);
        assertEquals(1, result.size());
    }
}
