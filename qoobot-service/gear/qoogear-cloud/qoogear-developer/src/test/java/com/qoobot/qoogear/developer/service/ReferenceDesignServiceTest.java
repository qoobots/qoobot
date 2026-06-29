package com.qoobot.qoogear.developer.service;

import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.developer.domain.ReferenceDesign;
import com.qoobot.qoogear.developer.repository.ReferenceDesignRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;

import java.time.ZonedDateTime;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit tests for ReferenceDesignService.
 */
@ExtendWith(MockitoExtension.class)
class ReferenceDesignServiceTest {

    @Mock private ReferenceDesignRepository designRepo;

    @InjectMocks
    private ReferenceDesignService service;

    private ReferenceDesign design;

    @BeforeEach
    void setUp() {
        design = new ReferenceDesign();
        design.setId(1L);
        design.setTitle("CAN-FD Gripper Reference Board");
        design.setCategory("gripper");
        design.setDescription("Open-source reference design for CAN-FD based robotic gripper");
        design.setFiles("{\"pcb\": \"gripper_v2.brd\", \"schematic\": \"gripper_v2.sch\"}");
        design.setDownloadCount(42L);
        design.setPublishedAt(ZonedDateTime.now());
    }

    @Test
    void shouldListDesignsByCategory() {
        Page<ReferenceDesign> page = new PageImpl<>(List.of(design));
        when(designRepo.findByCategory(eq("gripper"), any(Pageable.class))).thenReturn(page);

        var result = service.listDesigns("gripper", null, Pageable.unpaged());
        assertEquals(1, result.getTotal());
        assertEquals("CAN-FD Gripper Reference Board", result.getData().get(0).getTitle());
    }

    @Test
    void shouldListDesignsByKeyword() {
        Page<ReferenceDesign> page = new PageImpl<>(List.of(design));
        when(designRepo.findByTitleContainingIgnoreCase(eq("CAN-FD"), any(Pageable.class))).thenReturn(page);

        var result = service.listDesigns(null, "CAN-FD", Pageable.unpaged());
        assertEquals(1, result.getTotal());
    }

    @Test
    void shouldListAllDesigns() {
        Page<ReferenceDesign> page = new PageImpl<>(List.of(design));
        when(designRepo.findAll(any(Pageable.class))).thenReturn(page);

        var result = service.listDesigns(null, null, Pageable.unpaged());
        assertEquals(1, result.getTotal());
    }

    @Test
    void shouldGetDesignById() {
        when(designRepo.findById(1L)).thenReturn(Optional.of(design));
        ReferenceDesign result = service.getDesign(1L);
        assertNotNull(result);
        assertEquals("CAN-FD Gripper Reference Board", result.getTitle());
    }

    @Test
    void shouldThrowWhenDesignNotFound() {
        when(designRepo.findById(999L)).thenReturn(Optional.empty());
        assertThrows(QooGearException.class, () -> service.getDesign(999L));
    }

    @Test
    void shouldCreateDesign() {
        when(designRepo.save(any(ReferenceDesign.class))).thenAnswer(inv -> {
            ReferenceDesign d = inv.getArgument(0);
            d.setId(2L);
            return d;
        });

        ReferenceDesign newDesign = new ReferenceDesign();
        newDesign.setTitle("IMU Sensor Reference");
        newDesign.setCategory("sensor");
        newDesign.setFiles("{}");

        ReferenceDesign result = service.createDesign(newDesign);
        assertNotNull(result);
        assertNotNull(result.getPublishedAt());
        assertEquals("IMU Sensor Reference", result.getTitle());
    }

    @Test
    void shouldIncrementDownloads() {
        when(designRepo.findById(1L)).thenReturn(Optional.of(design));
        when(designRepo.save(any(ReferenceDesign.class))).thenReturn(design);

        service.incrementDownloads(1L);
        assertEquals(43L, design.getDownloadCount());
    }

    @Test
    void shouldIncrementDownloadsFromNull() {
        design.setDownloadCount(null);
        when(designRepo.findById(1L)).thenReturn(Optional.of(design));
        when(designRepo.save(any(ReferenceDesign.class))).thenReturn(design);

        service.incrementDownloads(1L);
        assertEquals(1L, design.getDownloadCount());
    }
}
