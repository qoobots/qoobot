package com.qoobot.qoochain.common.util;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/**
 * Material code generator.
 * Format: MAT-{CATEGORY}-{8-char hex hash}
 */
public class MaterialCodeGenerator {

    public static String generate(String category, String manufacturerPn) {
        String input = category + "-" + manufacturerPn + "-" + System.currentTimeMillis();
        String hash = sha256Hex(input).substring(0, 8).toUpperCase();
        return "MAT-" + category.toUpperCase() + "-" + hash;
    }

    public static String generateSupplierCode(String category, int sequence) {
        return String.format("SUP-%s-%04d", category.toUpperCase(), sequence);
    }

    private static String sha256Hex(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(input.getBytes());
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }
}
