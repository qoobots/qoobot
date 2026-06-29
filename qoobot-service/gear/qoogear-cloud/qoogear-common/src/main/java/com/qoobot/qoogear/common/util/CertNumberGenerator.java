package com.qoobot.qoogear.common.util;

import java.time.Year;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Generates MFQ certificate numbers in format: MFQ-YYYY-XXXXXX
 */
public final class CertNumberGenerator {

    private static final String PREFIX = "MFQ";

    private CertNumberGenerator() {}

    public static String generate() {
        int year = Year.now().getValue();
        int sequence = ThreadLocalRandom.current().nextInt(100000, 999999);
        return String.format("%s-%d-%06d", PREFIX, year, sequence);
    }

    public static String generateForLevel(String certLevel) {
        String base = generate();
        return base + "-" + certLevel.substring(0, 1);
    }
}
