package com.qoobot.qooauth.common.util;

import java.security.SecureRandom;
import java.util.Base64;

/**
 * ID generator for producing collision-resistant identifiers
 * in the format: {prefix}_ + 28 random URL-safe characters.
 */
public final class IdGenerator {

    private static final SecureRandom RANDOM = new SecureRandom();
    private static final Base64.Encoder ENCODER = Base64.getUrlEncoder().withoutPadding();
    private static final int RANDOM_BYTES = 21; // 21 bytes → 28 Base64URL chars

    private IdGenerator() {}

    public static String generateUserId() {
        return "uid_" + generateRandom();
    }

    public static String generateDeviceId() {
        return "dev_" + generateRandom();
    }

    public static String generateApiKeyId() {
        return "ak_" + generateRandom();
    }

    public static String generateSessionId() {
        return "ses_" + generateRandom();
    }

    public static String generateOAuthCode() {
        return "oc_" + generateRandom();
    }

    public static String generateLoginHistoryId() {
        return "lh_" + generateRandom();
    }

    public static String generateTrustedDeviceId() {
        return "td_" + generateRandom();
    }

    public static String generateApiKeyUsageId() {
        return "aku_" + generateRandom();
    }

    public static String generateDeviceCertId() {
        return "dc_" + generateRandom();
    }

    public static String generateCrlEntryId() {
        return "crl_" + generateRandom();
    }

    public static String generateCaConfigId() {
        return "ca_" + generateRandom();
    }

    public static String generateActivationId() {
        return "act_" + generateRandom();
    }

    public static String generateActivationChallengeId() {
        return "ach_" + generateRandom();
    }

    public static String generateAnomalyEventId() {
        return "ano_" + generateRandom();
    }

    public static String generateDeviceFingerprintId() {
        return "dfp_" + generateRandom();
    }

    public static String generateIpReputationId() {
        return "ipr_" + generateRandom();
    }

    public static String generateTrustGroupId() {
        return "tgr_" + generateRandom();
    }

    public static String generateMembershipId() {
        return "mem_" + generateRandom();
    }

    public static String generateDelegationId() {
        return "del_" + generateRandom();
    }

    public static String generateDeveloperCertId() {
        return "dvc_" + generateRandom();
    }

    public static String generateSkillSignatureId() {
        return "sks_" + generateRandom();
    }

    public static String generateSandboxEnvId() {
        return "sbx_" + generateRandom();
    }

    public static String generatePermissionReviewId() {
        return "prv_" + generateRandom();
    }

    private static String generateRandom() {
        byte[] bytes = new byte[RANDOM_BYTES];
        RANDOM.nextBytes(bytes);
        return ENCODER.encodeToString(bytes);
    }
}
