package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.dto.TokenResponse;
import com.qoobot.qooauth.auth.service.MfaService;
import com.qoobot.qooauth.auth.service.MfaService.*;
import com.qoobot.qooauth.common.dto.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * MFA (Multi-Factor Authentication) controller.
 *
 * Endpoints:
 *   POST   /api/v1/auth/mfa/totp/setup     - Generate TOTP secret + QR URI
 *   POST   /api/v1/auth/mfa/totp/verify     - Verify TOTP setup code
 *   POST   /api/v1/auth/mfa/totp/login      - Verify TOTP during login
 *   POST   /api/v1/auth/mfa/fido2/register/start   - Start FIDO2 registration
 *   POST   /api/v1/auth/mfa/fido2/register/complete - Complete FIDO2 registration
 *   POST   /api/v1/auth/mfa/fido2/login/start    - Start FIDO2 login assertion
 *   POST   /api/v1/auth/mfa/fido2/login/complete - Complete FIDO2 login assertion
 *   POST   /api/v1/auth/mfa/recovery/login   - Verify recovery code during login
 *   GET    /api/v1/auth/mfa/status           - Get MFA status
 *   POST   /api/v1/auth/mfa/recovery/regenerate - Regenerate recovery codes
 *   DELETE /api/v1/auth/mfa/method            - Remove an MFA method
 *   DELETE /api/v1/auth/mfa                   - Disable all MFA
 */
@RestController
@RequestMapping("/api/v1/auth/mfa")
public class MfaController {

    private final MfaService mfaService;

    public MfaController(MfaService mfaService) {
        this.mfaService = mfaService;
    }

    // ==================== TOTP ====================

    /**
     * Start TOTP setup: generates a secret and otpauth:// URI.
     * Requires authentication (Bearer token).
     */
    @PostMapping("/totp/setup")
    public ResponseEntity<ApiResponse<TotpSetupResult>> setupTotp(
            @RequestAttribute("userId") String userId,
            @RequestAttribute("email") String email) {
        TotpSetupResult result = mfaService.setupTotp(userId, email);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    /**
     * Verify TOTP setup code to enable TOTP as MFA method.
     */
    @PostMapping("/totp/verify")
    public ResponseEntity<ApiResponse<MfaVerifyResult>> verifyTotpSetup(
            @RequestAttribute("userId") String userId,
            @RequestBody Map<String, String> body) {
        String code = body.get("code");
        if (code == null || code.isEmpty()) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("BAD_REQUEST", "code is required"));
        }
        MfaVerifyResult result = mfaService.verifyTotpSetup(userId, code);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    /**
     * Verify TOTP code during login MFA step.
     * Uses the mfaToken from the login response instead of a Bearer token.
     */
    @PostMapping("/totp/login")
    public ResponseEntity<ApiResponse<TokenResponse>> verifyTotpLogin(
            @RequestBody Map<String, String> body,
            HttpServletRequest httpRequest) {
        String mfaToken = body.get("mfa_token");
        String code = body.get("code");

        if (mfaToken == null || code == null) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("BAD_REQUEST", "mfa_token and code are required"));
        }

        String ip = getClientIp(httpRequest);
        String userAgent = httpRequest.getHeader("User-Agent");
        String deviceFingerprint = httpRequest.getHeader("X-Device-Fingerprint");

        var result = mfaService.verifyTotpLogin(
                mfaToken, code, deviceFingerprint, "qoobot_api", ip, userAgent);

        return ResponseEntity.ok(
                ApiResponse.ok(TokenResponse.fromTokenPair(result.tokens(), result.user())));
    }

    // ==================== FIDO2/WebAuthn ====================

    /**
     * Start FIDO2/WebAuthn credential registration.
     * Returns a challenge for navigator.credentials.create().
     */
    @PostMapping("/fido2/register/start")
    public ResponseEntity<ApiResponse<Fido2RegistrationChallenge>> startFido2Registration(
            @RequestAttribute("userId") String userId) {
        Fido2RegistrationChallenge challenge = mfaService.startFido2Registration(userId);
        return ResponseEntity.ok(ApiResponse.ok(challenge));
    }

    /**
     * Complete FIDO2/WebAuthn credential registration.
     * Receives the attestation result from the browser.
     */
    @PostMapping("/fido2/register/complete")
    public ResponseEntity<ApiResponse<MfaVerifyResult>> completeFido2Registration(
            @RequestAttribute("userId") String userId,
            @RequestBody Map<String, Object> body) {
        String credentialId = (String) body.get("credential_id");
        String publicKey = (String) body.get("public_key");
        String credentialName = (String) body.getOrDefault("credential_name", "Security Key");
        long signCount = ((Number) body.getOrDefault("sign_count", 0)).longValue();
        String transports = (String) body.get("transports");
        String aaguid = (String) body.get("aaguid");
        String attestation = (String) body.get("attestation");

        if (credentialId == null || publicKey == null) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("BAD_REQUEST", "credential_id and public_key are required"));
        }

        MfaVerifyResult result = mfaService.completeFido2Registration(
                userId, credentialId, publicKey, credentialName,
                signCount, transports, aaguid, attestation);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(result));
    }

    /**
     * Start FIDO2/WebAuthn assertion for login verification.
     */
    @PostMapping("/fido2/login/start")
    public ResponseEntity<ApiResponse<Fido2AssertionChallenge>> startFido2Login(
            @RequestBody Map<String, String> body) {
        String mfaToken = body.get("mfa_token");
        if (mfaToken == null) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("BAD_REQUEST", "mfa_token is required"));
        }

        // userId is extracted from mfaToken by the service; client must also supply it
        String userId = body.get("user_id");
        if (userId == null) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("BAD_REQUEST", "user_id is required for FIDO2 login start"));
        }

        Fido2AssertionChallenge challenge = mfaService.startFido2Login(userId);
        return ResponseEntity.ok(ApiResponse.ok(challenge));
    }

    /**
     * Complete FIDO2/WebAuthn assertion for login verification.
     */
    @PostMapping("/fido2/login/complete")
    public ResponseEntity<ApiResponse<TokenResponse>> completeFido2Login(
            @RequestBody Map<String, Object> body,
            HttpServletRequest httpRequest) {
        String mfaToken = (String) body.get("mfa_token");
        String credentialId = (String) body.get("credential_id");
        long newSignCount = ((Number) body.getOrDefault("sign_count", 0)).longValue();

        if (mfaToken == null || credentialId == null) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("BAD_REQUEST", "mfa_token and credential_id are required"));
        }

        String ip = getClientIp(httpRequest);
        String userAgent = httpRequest.getHeader("User-Agent");
        String deviceFingerprint = httpRequest.getHeader("X-Device-Fingerprint");

        var result = mfaService.verifyFido2Login(
                mfaToken, credentialId, newSignCount,
                deviceFingerprint, "qoobot_api", ip, userAgent);

        return ResponseEntity.ok(
                ApiResponse.ok(TokenResponse.fromTokenPair(result.tokens(), result.user())));
    }

    // ==================== Recovery Codes ====================

    /**
     * Verify login using a one-time recovery code.
     */
    @PostMapping("/recovery/login")
    public ResponseEntity<ApiResponse<TokenResponse>> verifyRecoveryCodeLogin(
            @RequestBody Map<String, String> body,
            HttpServletRequest httpRequest) {
        String mfaToken = body.get("mfa_token");
        String recoveryCode = body.get("recovery_code");

        if (mfaToken == null || recoveryCode == null) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("BAD_REQUEST", "mfa_token and recovery_code are required"));
        }

        String ip = getClientIp(httpRequest);
        String userAgent = httpRequest.getHeader("User-Agent");
        String deviceFingerprint = httpRequest.getHeader("X-Device-Fingerprint");

        var result = mfaService.verifyRecoveryCodeLogin(
                mfaToken, recoveryCode, deviceFingerprint, "qoobot_api", ip, userAgent);

        return ResponseEntity.ok(
                ApiResponse.ok(TokenResponse.fromTokenPair(result.tokens(), result.user())));
    }

    /**
     * Regenerate recovery codes (invalidates old ones).
     * Requires authentication.
     */
    @PostMapping("/recovery/regenerate")
    public ResponseEntity<ApiResponse<List<String>>> regenerateRecoveryCodes(
            @RequestAttribute("userId") String userId) {
        List<String> codes = mfaService.regenerateRecoveryCodes(userId);
        return ResponseEntity.ok(ApiResponse.ok(codes));
    }

    // ==================== MFA Status & Management ====================

    /**
     * Get current MFA status for the authenticated user.
     */
    @GetMapping("/status")
    public ResponseEntity<ApiResponse<MfaStatus>> getMfaStatus(
            @RequestAttribute("userId") String userId) {
        MfaStatus status = mfaService.getMfaStatus(userId);
        return ResponseEntity.ok(ApiResponse.ok(status));
    }

    /**
     * Remove a specific MFA method.
     */
    @DeleteMapping("/method")
    public ResponseEntity<ApiResponse<Void>> removeMfaMethod(
            @RequestAttribute("userId") String userId,
            @RequestBody Map<String, String> body) {
        String methodType = body.get("method_type");
        String methodId = body.get("method_id");

        if (methodType == null) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("BAD_REQUEST", "method_type is required"));
        }

        mfaService.disableMfaMethod(userId, methodType, methodId);
        return ResponseEntity.noContent().build();
    }

    /**
     * Disable all MFA for the authenticated user.
     * Requires password confirmation.
     */
    @DeleteMapping
    public ResponseEntity<ApiResponse<Void>> disableAllMfa(
            @RequestAttribute("userId") String userId,
            @RequestBody Map<String, String> body) {
        String password = body.get("password");

        if (password == null || password.isEmpty()) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("BAD_REQUEST", "password is required to disable MFA"));
        }

        mfaService.disableAllMfa(userId, password);
        return ResponseEntity.noContent().build();
    }

    // ==================== Helpers ====================

    private String getClientIp(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
