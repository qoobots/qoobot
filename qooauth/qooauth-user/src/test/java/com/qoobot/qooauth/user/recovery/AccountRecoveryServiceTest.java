package com.qoobot.qooauth.user.recovery;

import com.qoobot.qooauth.user.dto.RecoveryCodeGenerateResponse;
import com.qoobot.qooauth.user.dto.RecoveryInitiateRequest;
import com.qoobot.qooauth.user.dto.RecoverySessionResponse;
import com.qoobot.qooauth.user.dto.RecoveryVerifyRequest;
import com.qoobot.qooauth.user.entity.RecoveryCodeEntity;
import com.qoobot.qooauth.user.entity.UserEntity;
import com.qoobot.qooauth.user.repository.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AccountRecoveryServiceTest {

    @Mock
    private UserEntityRepository userRepository;
    @Mock
    private RecoveryCodeRepository recoveryCodeRepository;
    @Mock
    private BackupEmailRepository backupEmailRepository;
    @Mock
    private RecoverySessionRepository recoverySessionRepository;

    private AccountRecoveryService service;
    private UserEntity testUser;

    @BeforeEach
    void setUp() {
        service = new AccountRecoveryService(userRepository, recoveryCodeRepository,
                backupEmailRepository, recoverySessionRepository);

        testUser = new UserEntity();
        testUser.setUserId("uid_test001");
        testUser.setEmail("test@example.com");
        testUser.setState("ACTIVE");
    }

    @Test
    void generateRecoveryCodes_ShouldReturnPlaintextCodes() {
        when(userRepository.findById("uid_test001")).thenReturn(Optional.of(testUser));
        when(recoveryCodeRepository.countByUserIdAndUsedFalse("uid_test001")).thenReturn(0L);
        when(recoveryCodeRepository.save(any())).thenReturn(new RecoveryCodeEntity());

        RecoveryCodeGenerateResponse response = service.generateRecoveryCodes("uid_test001", "My Codes");

        assertNotNull(response);
        assertNotNull(response.getRecoveryCodes());
        assertEquals(8, response.getCount());
        // Each code should have 3 dashes (4-4-4-4 format for 16 chars)
        for (String code : response.getRecoveryCodes()) {
            assertTrue(code.contains("-"), "Recovery code should contain dashes");
            assertEquals(19, code.length(), "Code should be 19 chars (16+3 dashes)");
        }
    }

    @Test
    void listRecoveryCodes_ShouldReturnMaskedList() {
        RecoveryCodeEntity code = new RecoveryCodeEntity();
        code.setId(1L);
        code.setLabel("Test Code");
        code.setCreatedAt(Instant.now());

        when(recoveryCodeRepository.findByUserIdAndUsedFalse("uid_test001"))
                .thenReturn(List.of(code));

        List<Map<String, Object>> codes = service.listRecoveryCodes("uid_test001");

        assertNotNull(codes);
        assertEquals(1, codes.size());
        assertEquals(1L, codes.get(0).get("id"));
        assertEquals("Test Code", codes.get(0).get("label"));
        assertNotNull(codes.get(0).get("created_at"));
    }

    @Test
    void initiateRecovery_ShouldReturnAvailableMethods() {
        when(userRepository.findByEmail("test@example.com")).thenReturn(Optional.of(testUser));
        when(recoveryCodeRepository.countByUserIdAndUsedFalse("uid_test001")).thenReturn(2L);
        when(backupEmailRepository.findByUserIdAndVerifiedTrue("uid_test001")).thenReturn(List.of());
        when(recoverySessionRepository.save(any())).thenAnswer(inv -> {
            RecoverySessionEntity s = inv.getArgument(0);
            s.setId(1L);
            return s;
        });

        RecoveryInitiateRequest request = new RecoveryInitiateRequest();
        request.setEmail("test@example.com");

        RecoverySessionResponse response = service.initiateRecovery(request, "127.0.0.1", "TestUA/1.0");

        assertNotNull(response);
        assertNotNull(response.getSessionToken());
        assertEquals("INITIATED", response.getState());
        assertTrue(response.getAvailableMethods().contains("RECOVERY_CODE"));
        assertTrue(response.getAvailableMethods().contains("TRUSTED_DEVICE"));
        assertEquals("t***t@example.com", response.getMaskedEmail());
        assertEquals(5, response.getAttemptsRemaining());
        assertNotNull(response.getExpiresAt());
    }

    @Test
    void initiateRecovery_DeletedAccount_ShouldThrow() {
        testUser.setState("DELETED");
        when(userRepository.findByEmail("test@example.com")).thenReturn(Optional.of(testUser));

        RecoveryInitiateRequest request = new RecoveryInitiateRequest();
        request.setEmail("test@example.com");

        assertThrows(Exception.class, () ->
                service.initiateRecovery(request, "127.0.0.1", "TestUA/1.0"));
    }
}
