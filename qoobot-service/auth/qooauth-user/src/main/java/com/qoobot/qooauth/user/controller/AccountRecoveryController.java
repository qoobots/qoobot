package com.qoobot.qooauth.user.controller;

import com.qoobot.qooauth.common.dto.ApiResponse;
import com.qoobot.qooauth.user.dto.*;
import com.qoobot.qooauth.user.recovery.AccountRecoveryService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Account recovery endpoints.
 * Recovery codes, backup email management, and recovery flow.
 */
@RestController
@RequestMapping("/api/v1/account")
public class AccountRecoveryController {

    private final AccountRecoveryService recoveryService;

    public AccountRecoveryController(AccountRecoveryService recoveryService) {
        this.recoveryService = recoveryService;
    }

    // ==================== Recovery Codes ====================

    /**
     * Generate new recovery codes (one-time display).
     */
    @PostMapping("/recovery-codes")
    public ResponseEntity<ApiResponse<RecoveryCodeGenerateResponse>> generateRecoveryCodes(
            @RequestAttribute("userId") String userId,
            @RequestBody RecoveryCodeGenerateRequest request) {
        RecoveryCodeGenerateResponse response = recoveryService.generateRecoveryCodes(userId, request.getLabel());
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(response));
    }

    /**
     * List active (unused) recovery codes (masked).
     */
    @GetMapping("/recovery-codes")
    public ResponseEntity<ApiResponse<List<Map<String, Object>>>> listRecoveryCodes(
            @RequestAttribute("userId") String userId) {
        return ResponseEntity.ok(ApiResponse.ok(recoveryService.listRecoveryCodes(userId)));
    }

    /**
     * Revoke a specific recovery code.
     */
    @DeleteMapping("/recovery-codes/{codeId}")
    public ResponseEntity<ApiResponse<Void>> revokeRecoveryCode(
            @RequestAttribute("userId") String userId,
            @PathVariable Long codeId) {
        recoveryService.revokeRecoveryCode(userId, codeId);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    // ==================== Backup Email ====================

    /**
     * Add a backup email for recovery.
     */
    @PostMapping("/backup-emails")
    public ResponseEntity<ApiResponse<Map<String, Object>>> addBackupEmail(
            @RequestAttribute("userId") String userId,
            @RequestBody BackupEmailRequest request) {
        Map<String, Object> result = recoveryService.addBackupEmail(userId, request.getEmail());
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(result));
    }

    /**
     * Verify a backup email with verification token.
     */
    @PostMapping("/backup-emails/verify")
    public ResponseEntity<ApiResponse<Void>> verifyBackupEmail(
            @RequestAttribute("userId") String userId,
            @RequestParam("token") String token) {
        recoveryService.verifyBackupEmail(userId, token);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    /**
     * Remove a backup email.
     */
    @DeleteMapping("/backup-emails/{emailId}")
    public ResponseEntity<ApiResponse<Void>> removeBackupEmail(
            @RequestAttribute("userId") String userId,
            @PathVariable Long emailId) {
        recoveryService.removeBackupEmail(userId, emailId);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    // ==================== Recovery Flow (public endpoints) ====================

    /**
     * Initiate account recovery. No authentication required.
     */
    @PostMapping("/recovery/initiate")
    public ResponseEntity<ApiResponse<RecoverySessionResponse>> initiateRecovery(
            @RequestBody RecoveryInitiateRequest request,
            HttpServletRequest httpRequest) {
        String ip = httpRequest.getRemoteAddr();
        String ua = httpRequest.getHeader("User-Agent");
        RecoverySessionResponse response = recoveryService.initiateRecovery(request, ip, ua);
        return ResponseEntity.ok(ApiResponse.ok(response));
    }

    /**
     * Verify a recovery step (submit code). No authentication required.
     */
    @PostMapping("/recovery/verify")
    public ResponseEntity<ApiResponse<RecoverySessionResponse>> verifyRecovery(
            @RequestBody RecoveryVerifyRequest request) {
        RecoverySessionResponse response = recoveryService.verifyRecoveryStep(request);
        return ResponseEntity.ok(ApiResponse.ok(response));
    }

    /**
     * Complete recovery (set new password). No authentication required.
     */
    @PostMapping("/recovery/complete")
    public ResponseEntity<ApiResponse<Map<String, Object>>> completeRecovery(
            @RequestBody RecoveryCompleteRequest request) {
        Map<String, Object> result = recoveryService.completeRecovery(request);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    /**
     * Check recovery session status.
     */
    @GetMapping("/recovery/session/{sessionToken}")
    public ResponseEntity<ApiResponse<RecoverySessionResponse>> getSessionStatus(
            @PathVariable String sessionToken) {
        return ResponseEntity.ok(ApiResponse.ok(recoveryService.getSessionStatus(sessionToken)));
    }
}
