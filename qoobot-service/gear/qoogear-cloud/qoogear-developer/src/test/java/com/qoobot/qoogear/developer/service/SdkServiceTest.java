package com.qoobot.qoogear.developer.service;

import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.developer.domain.SdkRelease;
import com.qoobot.qoogear.developer.repository.SdkReleaseRepository;
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
 * Unit tests for SdkService.
 */
@ExtendWith(MockitoExtension.class)
class SdkServiceTest {

    @Mock private SdkReleaseRepository sdkRepo;

    @InjectMocks
    private SdkService service;

    private SdkRelease pythonSdk;
    private SdkRelease cppSdk;

    @BeforeEach
    void setUp() {
        pythonSdk = new SdkRelease();
        pythonSdk.setId(1L);
        pythonSdk.setPlatform("python");
        pythonSdk.setVersion("2.1.0");
        pythonSdk.setDownloadUrl("https://releases.qoogear.com/sdk/python/2.1.0.tar.gz");
        pythonSdk.setFileSize(15_728_640L);
        pythonSdk.setChecksumSha256("abc123def456");
        pythonSdk.setReleaseNotes("Added peripheral simulator, improved CAN-FD support");
        pythonSdk.setIsLatest(true);
        pythonSdk.setReleasedAt(ZonedDateTime.now());

        cppSdk = new SdkRelease();
        cppSdk.setId(2L);
        cppSdk.setPlatform("cpp");
        cppSdk.setVersion("1.5.0");
        cppSdk.setDownloadUrl("https://releases.qoogear.com/sdk/cpp/1.5.0.zip");
        cppSdk.setFileSize(22_456_320L);
        cppSdk.setChecksumSha256("def789abc123");
        cppSdk.setIsLatest(true);
        cppSdk.setReleasedAt(ZonedDateTime.now());
    }

    @Test
    void shouldListReleasesByPlatform() {
        when(sdkRepo.findByPlatform("python")).thenReturn(List.of(pythonSdk));
        List<SdkRelease> result = service.listReleases("python");
        assertEquals(1, result.size());
        assertEquals("2.1.0", result.get(0).getVersion());
    }

    @Test
    void shouldGetLatestRelease() {
        when(sdkRepo.findByPlatformAndIsLatestTrue("python")).thenReturn(Optional.of(pythonSdk));
        SdkRelease result = service.getLatest("python");
        assertNotNull(result);
        assertEquals("2.1.0", result.getVersion());
        assertTrue(result.getIsLatest());
    }

    @Test
    void shouldThrowWhenNoLatestRelease() {
        when(sdkRepo.findByPlatformAndIsLatestTrue("rust")).thenReturn(Optional.empty());
        assertThrows(QooGearException.class, () -> service.getLatest("rust"));
    }

    @Test
    void shouldGetReleaseById() {
        when(sdkRepo.findById(1L)).thenReturn(Optional.of(pythonSdk));
        SdkRelease result = service.getRelease(1L);
        assertNotNull(result);
        assertEquals("python", result.getPlatform());
    }

    @Test
    void shouldThrowWhenReleaseNotFound() {
        when(sdkRepo.findById(999L)).thenReturn(Optional.empty());
        assertThrows(QooGearException.class, () -> service.getRelease(999L));
    }

    @Test
    void shouldPublishNewRelease() {
        SdkRelease newRelease = new SdkRelease();
        newRelease.setPlatform("python");
        newRelease.setVersion("3.0.0");
        newRelease.setDownloadUrl("https://releases.qoogear.com/sdk/python/3.0.0.tar.gz");
        newRelease.setIsLatest(true);

        when(sdkRepo.save(any(SdkRelease.class))).thenAnswer(inv -> {
            SdkRelease r = inv.getArgument(0);
            r.setId(3L);
            return r;
        });

        SdkRelease result = service.publishRelease(newRelease);
        assertNotNull(result);
        assertNotNull(result.getReleasedAt());
        verify(sdkRepo).resetLatestForPlatform("python");
    }

    @Test
    void shouldSetAsLatest() {
        when(sdkRepo.findById(2L)).thenReturn(Optional.of(cppSdk));
        when(sdkRepo.save(any(SdkRelease.class))).thenReturn(cppSdk);

        SdkRelease result = service.setAsLatest(2L);
        assertTrue(result.getIsLatest());
        verify(sdkRepo).resetLatestForPlatform("cpp");
    }
}
