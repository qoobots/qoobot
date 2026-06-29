package com.qoobot.qoostore.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 证书签名服务
 * 技能包 Ed25519 签名验证、平台证书签发
 * 对标 Apple App Store 的代码签名体系
 */
@Slf4j
@Service
public class SignatureService {

    @Value("${store.signing.private-key:}")
    private String platformPrivateKeyBase64;

    @Value("${store.signing.certificate:}")
    private String platformCertificateBase64;

    // 开发者公钥存储（生产环境用数据库）
    private final ConcurrentHashMap<String, String> developerPublicKeys = new ConcurrentHashMap<>();

    /**
     * 注册开发者公钥
     */
    public void registerDeveloperKey(String developerId, String publicKeyBase64) {
        developerPublicKeys.put(developerId, publicKeyBase64);
        log.info("Developer public key registered: developerId={}", developerId);
    }

    /**
     * 获取开发者公钥
     */
    public String getDeveloperPublicKey(String developerId) {
        return developerPublicKeys.get(developerId);
    }

    /**
     * 撤销开发者公钥
     */
    public void revokeDeveloperKey(String developerId) {
        developerPublicKeys.remove(developerId);
        log.warn("Developer public key revoked: developerId={}", developerId);
    }

    /**
     * 验证技能包签名
     * @param packageData 技能包数据
     * @param signature 开发者签名 (Base64)
     * @param developerId 开发者ID
     * @return 验证结果
     */
    public SignatureVerificationResult verifyPackageSignature(byte[] packageData, String signature, String developerId) {
        String publicKeyBase64 = developerPublicKeys.get(developerId);
        if (publicKeyBase64 == null) {
            return SignatureVerificationResult.failure("Developer public key not found: " + developerId);
        }

        try {
            byte[] publicKeyBytes = Base64.getDecoder().decode(publicKeyBase64);
            X509EncodedKeySpec keySpec = new X509EncodedKeySpec(publicKeyBytes);
            KeyFactory keyFactory = KeyFactory.getInstance("Ed25519");
            PublicKey publicKey = keyFactory.generatePublic(keySpec);

            Signature sig = Signature.getInstance("Ed25519");
            sig.initVerify(publicKey);
            sig.update(packageData);

            byte[] signatureBytes = Base64.getDecoder().decode(signature);
            boolean valid = sig.verify(signatureBytes);

            if (valid) {
                log.info("Package signature verified: developerId={}", developerId);
                return SignatureVerificationResult.success();
            } else {
                log.warn("Package signature verification failed: developerId={}", developerId);
                return SignatureVerificationResult.failure("Invalid signature");
            }
        } catch (Exception e) {
            log.error("Signature verification error: developerId={}, error={}", developerId, e.getMessage());
            return SignatureVerificationResult.failure("Verification error: " + e.getMessage());
        }
    }

    /**
     * 平台共签（开发者签名验证通过后，平台进行二次签名）
     * @param packageHash 技能包 SHA-256 哈希
     * @return 平台签名 (Base64)
     */
    public String coSignPackage(String packageHash) {
        if (platformPrivateKeyBase64 == null || platformPrivateKeyBase64.isEmpty()) {
            log.warn("Platform private key not configured, skipping co-sign");
            return "";
        }

        try {
            byte[] privateKeyBytes = Base64.getDecoder().decode(platformPrivateKeyBase64);
            PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(privateKeyBytes);
            KeyFactory keyFactory = KeyFactory.getInstance("Ed25519");
            PrivateKey privateKey = keyFactory.generatePrivate(keySpec);

            Signature sig = Signature.getInstance("Ed25519");
            sig.initSign(privateKey);
            sig.update(packageHash.getBytes(StandardCharsets.UTF_8));

            byte[] signature = sig.sign();
            log.info("Package co-signed by platform");
            return Base64.getEncoder().encodeToString(signature);
        } catch (Exception e) {
            log.error("Platform co-sign failed: {}", e.getMessage());
            throw new RuntimeException("Platform co-sign failed", e);
        }
    }

    /**
     * 生成开发者密钥对（用于新开发者注册）
     * @return KeyPairInfo 包含公钥和私钥的Base64编码
     */
    public KeyPairInfo generateDeveloperKeyPair() {
        try {
            KeyPairGenerator keyGen = KeyPairGenerator.getInstance("Ed25519");
            KeyPair keyPair = keyGen.generateKeyPair();

            String publicKey = Base64.getEncoder().encodeToString(keyPair.getPublic().getEncoded());
            String privateKey = Base64.getEncoder().encodeToString(keyPair.getPrivate().getEncoded());

            return new KeyPairInfo(publicKey, privateKey);
        } catch (Exception e) {
            log.error("Failed to generate key pair: {}", e.getMessage());
            throw new RuntimeException("Key pair generation failed", e);
        }
    }

    /**
     * 验证平台签名（端侧使用）
     * @param packageHash 技能包哈希
     * @param platformSignature 平台签名
     * @return 是否有效
     */
    public boolean verifyPlatformSignature(String packageHash, String platformSignature) {
        if (platformCertificateBase64 == null || platformCertificateBase64.isEmpty()) {
            return false;
        }

        try {
            byte[] certBytes = Base64.getDecoder().decode(platformCertificateBase64);
            X509EncodedKeySpec keySpec = new X509EncodedKeySpec(certBytes);
            KeyFactory keyFactory = KeyFactory.getInstance("Ed25519");
            PublicKey publicKey = keyFactory.generatePublic(keySpec);

            Signature sig = Signature.getInstance("Ed25519");
            sig.initVerify(publicKey);
            sig.update(packageHash.getBytes(StandardCharsets.UTF_8));

            byte[] sigBytes = Base64.getDecoder().decode(platformSignature);
            return sig.verify(sigBytes);
        } catch (Exception e) {
            log.error("Platform signature verification error: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 签名验证结果
     */
    public record SignatureVerificationResult(boolean valid, String message) {
        public static SignatureVerificationResult success() {
            return new SignatureVerificationResult(true, "Signature verified successfully");
        }

        public static SignatureVerificationResult failure(String message) {
            return new SignatureVerificationResult(false, message);
        }
    }

    /**
     * 密钥对信息
     */
    public record KeyPairInfo(String publicKey, String privateKey) {}
}
