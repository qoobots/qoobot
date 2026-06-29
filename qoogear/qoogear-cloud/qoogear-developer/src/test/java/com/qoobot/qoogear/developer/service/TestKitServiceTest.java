package com.qoobot.qoogear.developer.service;

import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.developer.domain.TestKit;
import com.qoobot.qoogear.developer.repository.TestKitRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit tests for TestKitService.
 */
@ExtendWith(MockitoExtension.class)
class TestKitServiceTest {

    @Mock private TestKitRepository kitRepo;

    @InjectMocks
    private TestKitService service;

    private TestKit kit;

    @BeforeEach
    void setUp() {
        kit = new TestKit();
        kit.setId(1L);
        kit.setName("Gripper Test Fixture Kit");
        kit.setDescription("Complete test fixture for gripper certification");
        kit.setKitType("mechanical");
        kit.setPrice(new BigDecimal("1500.00"));
        kit.setCurrency("CNY");
        kit.setStock(25);
        kit.setIsAvailable(true);
        kit.setCompatibleStandards(List.of(1L, 2L));
    }

    @Test
    void shouldListAvailableKits() {
        when(kitRepo.findByIsAvailableTrue()).thenReturn(List.of(kit));
        List<TestKit> result = service.listAvailable();
        assertEquals(1, result.size());
        assertTrue(result.get(0).getIsAvailable());
    }

    @Test
    void shouldListKitsByType() {
        when(kitRepo.findByKitType("mechanical")).thenReturn(List.of(kit));
        List<TestKit> result = service.listByType("mechanical");
        assertEquals(1, result.size());
        assertEquals("mechanical", result.get(0).getKitType());
    }

    @Test
    void shouldGetKitById() {
        when(kitRepo.findById(1L)).thenReturn(Optional.of(kit));
        TestKit result = service.getKit(1L);
        assertNotNull(result);
        assertEquals("Gripper Test Fixture Kit", result.getName());
    }

    @Test
    void shouldThrowWhenKitNotFound() {
        when(kitRepo.findById(999L)).thenReturn(Optional.empty());
        assertThrows(QooGearException.class, () -> service.getKit(999L));
    }

    @Test
    void shouldCreateKit() {
        when(kitRepo.save(any(TestKit.class))).thenReturn(kit);
        TestKit result = service.createKit(kit);
        assertNotNull(result);
        assertEquals(new BigDecimal("1500.00"), result.getPrice());
    }

    @Test
    void shouldUpdateStockAndSetAvailability() {
        when(kitRepo.findById(1L)).thenReturn(Optional.of(kit));
        when(kitRepo.save(any(TestKit.class))).thenReturn(kit);

        TestKit result = service.updateStock(1L, 50);
        assertEquals(50, result.getStock());
        assertTrue(result.getIsAvailable());
    }

    @Test
    void shouldSetUnavailableWhenStockIsZero() {
        when(kitRepo.findById(1L)).thenReturn(Optional.of(kit));
        when(kitRepo.save(any(TestKit.class))).thenReturn(kit);

        TestKit result = service.updateStock(1L, 0);
        assertEquals(0, result.getStock());
        assertFalse(result.getIsAvailable());
    }
}
