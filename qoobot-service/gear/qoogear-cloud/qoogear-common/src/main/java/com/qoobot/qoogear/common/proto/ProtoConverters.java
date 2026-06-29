package com.qoobot.qoogear.common.proto;

import java.util.Map;

/**
 * Proto message converter utilities.
 *
 * Maps between Java domain objects and Protobuf-defined message structures
 * defined in proto/ (certification.proto, standard.proto, peripheral.proto).
 *
 * These converters enable gRPC/gRPC-web integration for:
 *  - Real-time accessory discovery and registration (peripheral.proto)
 *  - Standardized certification data exchange (certification.proto)
 *  - Interface standard versioning (standard.proto)
 *
 * Note: For full protobuf compilation, add protobuf-maven-plugin to pom.xml.
 * These converters provide manual mapping until protobuf code generation is configured.
 */
public final class ProtoConverters {

    private ProtoConverters() {}

    // === Certification Proto (certification.proto) ===

    /**
     * Convert a Java Map to a certification.proto compatible CertificationApplication message.
     */
    public static Map<String, Object> toCertificationProto(Map<String, Object> domain) {
        return Map.of(
                "application_id", domain.getOrDefault("id", "").toString(),
                "product", Map.of(
                        "name", domain.getOrDefault("productName", ""),
                        "model_number", domain.getOrDefault("productModel", ""),
                        "description", domain.getOrDefault("description", ""),
                        "category", categoryToProto((String) domain.getOrDefault("productCategory", "gripper"))
                ),
                "target_level", levelToProto((String) domain.getOrDefault("certLevel", "basic")),
                "status", statusToProto((String) domain.getOrDefault("status", "draft")),
                "submitted_at", domain.getOrDefault("submittedAt", "").toString(),
                "assigned_lab_id", domain.getOrDefault("assignedLabId", "").toString()
        );
    }

    /**
     * Convert certification.proto ApplicationStatus enum value to domain string.
     */
    public static String statusFromProto(int protoStatus) {
        return switch (protoStatus) {
            case 1 -> "draft";
            case 2 -> "submitted";
            case 3 -> "compliance_check";
            case 4 -> "assigned";
            case 5 -> "testing";
            case 6 -> "test_completed";
            case 7 -> "test_completed";   // LAB_FAILED maps to test_completed with fail result
            case 8 -> "security_review";
            case 9 -> "approved";
            case 10 -> "rejected";
            case 11 -> "approved";         // CERTIFICATE_ISSUED is post-approved
            case 12 -> "revoked";
            case 13 -> "expired";
            default -> "draft";
        };
    }

    /**
     * Convert domain status string to certification.proto ApplicationStatus enum value.
     */
    public static int statusToProto(String domainStatus) {
        return switch (domainStatus.toLowerCase()) {
            case "draft" -> 1;
            case "submitted" -> 2;
            case "compliance_check" -> 3;
            case "assigned" -> 4;
            case "testing" -> 5;
            case "test_completed" -> 6;
            case "security_review" -> 8;
            case "approved" -> 9;
            case "rejected" -> 10;
            case "revoked" -> 12;
            case "expired" -> 13;
            default -> 0;
        };
    }

    /**
     * Convert domain cert level to certification.proto MfqLevel enum value.
     */
    public static int levelToProto(String level) {
        return switch (level.toLowerCase()) {
            case "basic" -> 1;
            case "premium" -> 2;
            case "pro" -> 3;
            default -> 0;
        };
    }

    /**
     * Convert domain category string to certification.proto ProductCategory enum value.
     */
    public static int categoryToProto(String category) {
        return switch (category.toLowerCase()) {
            case "gripper" -> 1;
            case "sensor" -> 2;
            case "wearable" -> 3;
            case "power" -> 4;
            case "mobility" -> 5;
            case "tool" -> 6;
            default -> 0;
        };
    }

    // === Standard Proto (standard.proto) ===

    /**
     * Convert domain status string to standard.proto SpecStatus enum value.
     */
    public static int specStatusToProto(String status) {
        return switch (status.toLowerCase()) {
            case "draft" -> 1;
            case "review" -> 2;
            case "published" -> 3;
            case "deprecated" -> 4;
            default -> 0;
        };
    }

    /**
     * Convert standard.proto SpecStatus enum value to domain string.
     */
    public static String specStatusFromProto(int protoStatus) {
        return switch (protoStatus) {
            case 1 -> "draft";
            case 2 -> "review";
            case 3 -> "published";
            case 4 -> "deprecated";
            case 5 -> "deprecated";  // SUPERSEDED treated as deprecated
            default -> "draft";
        };
    }

    /**
     * Convert compatibility status to standard.proto CompatibilityStatus enum value.
     */
    public static int compatStatusToProto(String status) {
        return switch (status.toLowerCase()) {
            case "compatible", "fully_compatible" -> 1;
            case "limited_compatible", "conditional" -> 2;
            case "not_compatible" -> 3;
            case "not_tested" -> 4;
            default -> 0;
        };
    }

    // === Peripheral Proto (peripheral.proto) ===

    /**
     * Convert accessory type to peripheral.proto AccessoryType enum value.
     */
    public static int accessoryTypeToProto(String type) {
        return switch (type.toLowerCase()) {
            case "gripper" -> 1;
            case "sensor" -> 2;
            case "wearable" -> 3;
            case "power" -> 4;
            case "mobility" -> 5;
            case "communication" -> 6;
            case "tool" -> 7;
            default -> 0;
        };
    }

    /**
     * Convert MFQ cert level to peripheral.proto MfqCertLevel enum value.
     */
    public static int mfqLevelToPeripheralProto(String level) {
        return levelToProto(level);  // Same enum values as certification proto
    }

    /**
     * Build a peripheral.proto CapabilityAnnouncement-compatible map.
     */
    public static Map<String, Object> toCapabilityAnnouncement(
            String vendorId, String productId, String name, String vendorName,
            String model, String type, String certHash, String certLevel) {
        return Map.of(
                "id", Map.of("vendor_id", vendorId, "product_id", productId),
                "name", name,
                "vendor_name", vendorName,
                "model", model,
                "firmware_version", "1.0.0",
                "type", accessoryTypeToProto(type),
                "mfq_cert_hash", certHash,
                "mfq_level", mfqLevelToPeripheralProto(certLevel)
        );
    }

    /**
     * Convert peripheral.proto AccessoryState enum value to string.
     */
    public static String accessoryStateFromProto(int state) {
        return switch (state) {
            case 1 -> "disconnected";
            case 2 -> "connecting";
            case 3 -> "connected";
            case 4 -> "ready";
            case 5 -> "active";
            case 6 -> "error";
            case 7 -> "emergency_stop";
            case 8 -> "firmware_update";
            default -> "unknown";
        };
    }

    /**
     * Convert peripheral.proto ResponseCode to human-readable message.
     */
    public static String responseCodeMessage(int code) {
        return switch (code) {
            case 0 -> "OK";
            case 1 -> "Invalid command";
            case 2 -> "Timeout";
            case 3 -> "Out of range";
            case 4 -> "Safety trip";
            case 5 -> "Not calibrated";
            case 6 -> "Busy";
            case 7 -> "Hardware fault";
            case 8 -> "Not supported";
            default -> "Unknown response code";
        };
    }
}
