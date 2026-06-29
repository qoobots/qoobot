package com.qoobot.qoocloud.data.service;

import org.springframework.stereotype.Service;

import java.util.List;
import java.util.regex.Pattern;

/**
 * PrivacyFilterService — 隐私过滤服务
 * 数据上传前自动脱敏：人脸、车牌、敏感文本
 */
@Service
public class PrivacyFilterService {

    // PII patterns
    private static final Pattern FACE_PATTERN = Pattern.compile(
        "face_encoding|face_landmark|biometric");
    private static final Pattern LICENSE_PLATE = Pattern.compile(
        "[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤川青藏琼宁][A-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9挂学警港澳]");
    private static final Pattern EMAIL_PATTERN = Pattern.compile(
        "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}");
    private static final Pattern PHONE_PATTERN = Pattern.compile(
        "1[3-9]\\d{9}");
    private static final Pattern ID_CARD_PATTERN = Pattern.compile(
        "\\d{17}[\\dXx]");
    private static final Pattern IP_ADDRESS_PATTERN = Pattern.compile(
        "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}");

    /**
     * Check if data contains sensitive biometric information.
     */
    public boolean containsBiometricData(String payload) {
        return FACE_PATTERN.matcher(payload).find();
    }

    /**
     * Filter PII from text data.
     * Replaces detected patterns with [REDACTED].
     */
    public String filterPII(String text) {
        if (text == null || text.isEmpty()) return text;

        return LICENSE_PLATE.matcher(
            EMAIL_PATTERN.matcher(
                PHONE_PATTERN.matcher(
                    ID_CARD_PATTERN.matcher(
                        IP_ADDRESS_PATTERN.matcher(text)
                            .replaceAll("[IP_REDACTED]"))
                        .replaceAll("[ID_REDACTED]"))
                    .replaceAll("[PHONE_REDACTED]"))
                .replaceAll("[EMAIL_REDACTED]"))
            .replaceAll("[PLATE_REDACTED]");
    }

    /**
     * Determine if data should be processed locally (on-device)
     * rather than uploaded to cloud.
     */
    public boolean shouldProcessLocally(String dataType, List<String> tags) {
        // Privacy-sensitive data should stay on-device
        if (tags.contains("biometric") || tags.contains("face") ||
            tags.contains("voice_print") || tags.contains("personal")) {
            return true;
        }

        // Large raw sensor data is better processed locally
        if ("raw_lidar".equals(dataType) || "raw_video".equals(dataType)) {
            return true;
        }

        return false;
    }

    /**
     * Compute privacy risk score for a data payload.
     * Returns 0.0 (no risk) to 1.0 (high risk).
     */
    public double computePrivacyRisk(String payload, List<String> tags) {
        double risk = 0.0;

        if (containsBiometricData(payload)) risk += 0.4;
        if (tags != null) {
            if (tags.contains("personal")) risk += 0.3;
            if (tags.contains("location")) risk += 0.2;
            if (tags.contains("audio")) risk += 0.1;
        }

        // Check for PII patterns in payload
        String filtered = filterPII(payload);
        if (!filtered.equals(payload)) {
            risk += 0.2;  // PII detected
        }

        return Math.min(risk, 1.0);
    }

    /**
     * Anonymize data using k-anonymity approach.
     */
    public String anonymize(String payload, int k) {
        if (k <= 1) return payload;

        // Simplified k-anonymity: generalize location precision
        // In production: full k-anonymity with generalization hierarchy
        return payload.replaceAll(
            "\\d{2,}\\.\\d{4,}", "XX.XXXX"  // Generalize coordinates
        );
    }

    /**
     * Apply differential privacy to numeric data.
     */
    public double applyDifferentialPrivacy(double value, double sensitivity, double epsilon) {
        // Laplace mechanism: add noise scaled by sensitivity/epsilon
        double scale = sensitivity / epsilon;
        double u = Math.random() - 0.5;
        double noise = -scale * Math.signum(u) * Math.log(1 - 2 * Math.abs(u));
        return value + noise;
    }

    /**
     * Generate a data minimization report.
     * Ensures only necessary data is collected.
     */
    public String generateMinimizationReport(String dataType, long bytesCollected) {
        return String.format(
            "Data minimization check for %s: %d bytes collected. " +
            "Recommendation: %s",
            dataType, bytesCollected,
            bytesCollected > 10_000_000 ?
                "Consider reducing data granularity or frequency" :
                "Data collection within acceptable bounds"
        );
    }
}
