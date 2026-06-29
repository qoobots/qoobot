package com.qoobot.qoogear.common.util;

import java.util.concurrent.ThreadLocalRandom;

/**
 * Generates specification numbers in format: MFQ-SPEC-XXXX
 */
public final class SpecNumberGenerator {

    private static final String PREFIX = "MFQ-SPEC";

    private SpecNumberGenerator() {}

    public static String generate() {
        int sequence = ThreadLocalRandom.current().nextInt(1000, 9999);
        return String.format("%s-%04d", PREFIX, sequence);
    }
}
