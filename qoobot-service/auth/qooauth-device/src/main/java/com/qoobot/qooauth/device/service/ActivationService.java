package com.qoobot.qooauth.device.service;

import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.device.entity.Device;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.Base64;
import java.util.Optional;
import java.util.UUID;

/**
 * Full device activation flow service.
 * <p>
 * Orchestrates the activation lifecycle:
 * <ol>
 *   <li>Validate the incoming PKCS#10 CSR</li>
 *   <li>Issue an X.509 device certificate via {@link CertificateService}</li>
 *   <li>Register the device via {@link DeviceService}</li>
 *   <li>Generate a one-time binding token (stored in Redis, TTL 24h)</li>
 *   <li>Return the device certificate and binding token to the caller</li>
 * </ol>
 */
@Service
public class ActivationService {

    private static final Logger log = LoggerFactory.getLogger(ActivationService.class);

    private static final String BINDING_TOKEN_PREFIX = "qooauth:binding_token:";
    private static final Duration BINDING_TOKEN_TTL = Duration.ofHours(24);

    private final DeviceService deviceService;
    private final CertificateService certificateService;
    private final RedisTemplate<String, String> redisTemplate;
    private final SecureRandom secureRandom;

    public ActivationService(DeviceService deviceService,
                             CertificateService certificateService,
                             RedisTemplate<String, String> redisTemplate) {
        this.deviceService = deviceService;
        this.certificateService = certificateService;
        this.redisTemplate = redisTemplate;
        this.secureRandom = new SecureRandom();
    }

    /**
     * Activate a device.
     * <p>
     * Full flow: validate CSR, issue certificate, register device, generate binding token.
     *
     * @param deviceSerial    factory serial number
     * @param hardwareModel   hardware model identifier
     * @param hardwareVersion optional hardware version
     * @param firmwareVersion optional firmware version
     * @param csrPem          PKCS#10 CSR in PEM format
     * @param cpuId           optional CPU identifier
     * @param macAddress      optional MAC address
     * @param tpmEkHash       optional TPM endorsement key hash
     * @param clientIp        client IP address
     * @return ActivationResult containing the device certificate and binding token
     */
    public ActivationResult activate(String deviceSerial, String hardwareModel,
                                     String hardwareVersion, String firmwareVersion,
                                     String csrPem,
                                     String cpuId, String macAddress, String tpmEkHash,
                                     String clientIp) {

        // Step 1: Check for duplicate serial
        Optional<Device> existing = deviceService.findByDeviceSerial(deviceSerial);
        if (existing.isPresent()) {
            log.warn("Device serial {} already registered as {}", deviceSerial, existing.get().getDeviceId());
            throw new AuthException(ErrorCodes.DEVICE_ALREADY_BOUND,
                    "Device with serial " + deviceSerial + " is already activated");
        }

        // Step 2: Register device (generates device_id)
        Device device = deviceService.register(deviceSerial, hardwareModel,
                hardwareVersion, firmwareVersion,
                "PENDING", // placeholder — updated after cert issuance
                null,
                OffsetDateTime.now().plusYears(5), // placeholder expiry
                cpuId, macAddress, tpmEkHash, clientIp);

        // Step 3: Issue X.509 device certificate
        String certPem;
        String certSerialNumber;
        try {
            certPem = certificateService.issueDeviceCertificate(csrPem, device.getDeviceId(), deviceSerial);
            var cert = certificateService.findBySerialNumber(
                    certificateService.findByDeviceId(device.getDeviceId()).stream()
                            .filter(c -> c.getState().equals("ACTIVE"))
                            .findFirst()
                            .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_CERT_ISSUE_FAILED, "Certificate was not persisted"))
                            .getSerialNumber());

            certSerialNumber = cert.getSerialNumber();

            // Update device with actual certificate info
            device.setCertificateSn(certSerialNumber);
            device.setCertificatePem(certPem);
            device.setCertificateExpiresAt(cert.getNotAfter());

        } catch (AuthException e) {
            throw e;
        } catch (Exception e) {
            log.error("Certificate issuance failed during activation for device {}", device.getDeviceId(), e);
            throw new AuthException(ErrorCodes.DEVICE_CERT_ISSUE_FAILED,
                    "Failed to issue device certificate: " + e.getMessage(), e);
        }

        // Step 4: Generate one-time binding token (store in Redis with 24h TTL)
        String bindingToken = generateBindingToken();
        redisTemplate.opsForValue().set(
                BINDING_TOKEN_PREFIX + bindingToken,
                device.getDeviceId(),
                BINDING_TOKEN_TTL);

        log.info("Device activated: deviceId={}, serial={}, bindingToken={}",
                device.getDeviceId(), deviceSerial,
                bindingToken.substring(0, 8) + "...");

        return new ActivationResult(
                device.getDeviceId(),
                deviceSerial,
                certPem,
                certSerialNumber,
                device.getCertificateExpiresAt(),
                bindingToken);
    }

    /**
     * Validate a binding token and return the associated device ID.
     *
     * @param bindingToken the token to validate
     * @return the device ID if the token is valid
     * @throws AuthException if the token is invalid or expired
     */
    public String validateBindingToken(String bindingToken) {
        String deviceId = redisTemplate.opsForValue().get(BINDING_TOKEN_PREFIX + bindingToken);
        if (deviceId == null) {
            log.warn("Invalid or expired binding token: {}...",
                    bindingToken.length() > 8 ? bindingToken.substring(0, 8) : bindingToken);
            throw new AuthException(ErrorCodes.DEVICE_ACTIVATION_EXPIRED,
                    "Binding token is invalid or has expired (24h TTL)");
        }
        return deviceId;
    }

    /**
     * Consume (delete) a binding token after successful binding.
     */
    public void consumeBindingToken(String bindingToken) {
        redisTemplate.delete(BINDING_TOKEN_PREFIX + bindingToken);
        log.debug("Binding token consumed: {}...",
                bindingToken.length() > 8 ? bindingToken.substring(0, 8) : bindingToken);
    }

    // --- Internal helpers ---

    private String generateBindingToken() {
        byte[] randomBytes = new byte[32];
        secureRandom.nextBytes(randomBytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(randomBytes);
    }

    // ========================================================================
    //  ActivationResult
    // ========================================================================

    /**
     * Result of a successful device activation.
     */
    public static class ActivationResult {
        private final String deviceId;
        private final String deviceSerial;
        private final String certificatePem;
        private final String certificateSerialNumber;
        private final OffsetDateTime certificateExpiresAt;
        private final String bindingToken;

        public ActivationResult(String deviceId, String deviceSerial, String certificatePem,
                                String certificateSerialNumber, OffsetDateTime certificateExpiresAt,
                                String bindingToken) {
            this.deviceId = deviceId;
            this.deviceSerial = deviceSerial;
            this.certificatePem = certificatePem;
            this.certificateSerialNumber = certificateSerialNumber;
            this.certificateExpiresAt = certificateExpiresAt;
            this.bindingToken = bindingToken;
        }

        public String getDeviceId() { return deviceId; }
        public String getDeviceSerial() { return deviceSerial; }
        public String getCertificatePem() { return certificatePem; }
        public String getCertificateSerialNumber() { return certificateSerialNumber; }
        public OffsetDateTime getCertificateExpiresAt() { return certificateExpiresAt; }
        public String getBindingToken() { return bindingToken; }
    }
}
