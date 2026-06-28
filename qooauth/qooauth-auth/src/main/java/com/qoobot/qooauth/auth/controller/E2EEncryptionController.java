package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.service.E2EEncryptionService;
import com.qoobot.qooauth.common.dto.ApiResponse;
import org.springframework.web.bind.annotation.*;

import java.security.*;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

/**
 * E2EE Controller.
 * <p>
 * Endpoints for end-to-end encryption key management:
 * <ul>
 *   <li>Generate identity key pairs</li>
 *   <li>Generate and upload pre-key bundles (X3DH)</li>
 *   <li>Fetch peer key bundles</li>
 *   <li>Exchange encrypted messages</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1/auth/e2ee")
public class E2EEncryptionController {

    private final E2EEncryptionService e2eEncryptionService;

    public E2EEncryptionController(E2EEncryptionService e2eEncryptionService) {
        this.e2eEncryptionService = e2eEncryptionService;
    }

    /**
     * Generate identity key pair and pre-key bundle for a user.
     */
    @PostMapping("/keys/generate")
    public ApiResponse<Map<String, Object>> generateKeys(@RequestParam String userId) {
        try {
            KeyPair identityKey = e2eEncryptionService.generateIdentityKeyPair();
            E2EEncryptionService.SignedPreKey signedPreKey = e2eEncryptionService.generateSignedPreKey(
                    identityKey.getPrivate());
            KeyPair oneTimePreKey = e2eEncryptionService.generateOneTimePreKey();

            // Build key bundle
            E2EEncryptionService.KeyBundle bundle = new E2EEncryptionService.KeyBundle(
                    identityKey.getPublic(),
                    signedPreKey,
                    oneTimePreKey.getPublic(),
                    1, // signed pre-key ID
                    1  // one-time pre-key ID
            );

            e2eEncryptionService.registerKeyBundle(userId, bundle);

            Map<String, Object> result = new HashMap<>();
            result.put("user_id", userId);
            result.put("identity_key", Base64.getEncoder().encodeToString(
                    identityKey.getPublic().getEncoded()));
            result.put("signed_pre_key_id", 1);
            result.put("signed_pre_key", Base64.getEncoder().encodeToString(
                    signedPreKey.getPublic().getEncoded()));
            result.put("signed_pre_key_signature", Base64.getEncoder().encodeToString(
                    signedPreKey.signature));
            result.put("one_time_pre_key_id", 1);
            result.put("one_time_pre_key", Base64.getEncoder().encodeToString(
                    oneTimePreKey.getPublic().getEncoded()));

            return ApiResponse.ok(result);
        } catch (Exception e) {
            return ApiResponse.error("E2EE_KEY_GENERATION_FAILED", e.getMessage());
        }
    }

    /**
     * Perform X3DH key agreement and encrypt a message.
     */
    @PostMapping("/encrypt")
    public ApiResponse<Map<String, Object>> encryptMessage(@RequestBody Map<String, String> body) {
        try {
            String senderId = body.get("sender_id");
            String receiverId = body.get("receiver_id");
            String plaintext = body.get("plaintext");

            if (senderId == null || receiverId == null || plaintext == null) {
                return ApiResponse.error("BAD_REQUEST", "sender_id, receiver_id, and plaintext are required");
            }

            E2EEncryptionService.RatchetMessage encrypted = e2eEncryptionService.encryptString(
                    senderId, receiverId, plaintext);

            Map<String, Object> result = new HashMap<>();
            result.put("ciphertext", encrypted.toBase64());
            result.put("message_number", encrypted.messageNumber);

            return ApiResponse.ok(result);
        } catch (Exception e) {
            return ApiResponse.error("E2EE_ENCRYPT_FAILED", e.getMessage());
        }
    }

    /**
     * Decrypt an E2EE message.
     */
    @PostMapping("/decrypt")
    public ApiResponse<Map<String, Object>> decryptMessage(@RequestBody Map<String, String> body) {
        try {
            String senderId = body.get("sender_id");
            String receiverId = body.get("receiver_id");
            String ciphertext = body.get("ciphertext");

            if (senderId == null || receiverId == null || ciphertext == null) {
                return ApiResponse.error("BAD_REQUEST", "sender_id, receiver_id, and ciphertext are required");
            }

            E2EEncryptionService.RatchetMessage message = E2EEncryptionService.RatchetMessage.fromBase64(ciphertext);
            String plaintext = e2eEncryptionService.decryptString(receiverId, senderId, message);

            Map<String, Object> result = new HashMap<>();
            result.put("plaintext", plaintext);
            result.put("message_number", message.messageNumber);

            return ApiResponse.ok(result);
        } catch (Exception e) {
            return ApiResponse.error("E2EE_DECRYPT_FAILED", e.getMessage());
        }
    }

    /**
     * Delete E2EE session (cleanup).
     */
    @DeleteMapping("/session")
    public ApiResponse<Map<String, String>> deleteSession(
            @RequestParam String userId1, @RequestParam String userId2) {
        e2eEncryptionService.deleteSession(userId1, userId2);
        return ApiResponse.ok(Map.of("status", "deleted"));
    }

    /**
     * Sign data with a user's Ed25519 identity key.
     */
    @PostMapping("/sign")
    public ApiResponse<Map<String, String>> signData(@RequestBody Map<String, String> body) {
        try {
            String privateKeyB64 = body.get("private_key");
            String data = body.get("data");

            if (privateKeyB64 == null || data == null) {
                return ApiResponse.error("BAD_REQUEST", "private_key and data are required");
            }

            KeyFactory kf = KeyFactory.getInstance("X25519");
            PrivateKey privateKey = kf.generatePrivate(
                    new X509EncodedKeySpec(Base64.getDecoder().decode(privateKeyB64)));
            byte[] signature = e2eEncryptionService.sign(privateKey, data.getBytes());

            return ApiResponse.ok(Map.of("signature", Base64.getEncoder().encodeToString(signature)));
        } catch (Exception e) {
            return ApiResponse.error("E2EE_SIGN_FAILED", e.getMessage());
        }
    }

    /**
     * Verify a signature.
     */
    @PostMapping("/verify")
    public ApiResponse<Map<String, Object>> verifySignature(@RequestBody Map<String, String> body) {
        try {
            String publicKeyB64 = body.get("public_key");
            String data = body.get("data");
            String signatureB64 = body.get("signature");

            if (publicKeyB64 == null || data == null || signatureB64 == null) {
                return ApiResponse.error("BAD_REQUEST", "public_key, data, and signature are required");
            }

            KeyFactory kf = KeyFactory.getInstance("X25519");
            PublicKey publicKey = kf.generatePublic(
                    new X509EncodedKeySpec(Base64.getDecoder().decode(publicKeyB64)));
            byte[] signature = Base64.getDecoder().decode(signatureB64);

            boolean valid = e2eEncryptionService.verify(publicKey, data.getBytes(), signature);

            return ApiResponse.ok(Map.of("valid", valid));
        } catch (Exception e) {
            return ApiResponse.error("E2EE_VERIFY_FAILED", e.getMessage());
        }
    }
}
