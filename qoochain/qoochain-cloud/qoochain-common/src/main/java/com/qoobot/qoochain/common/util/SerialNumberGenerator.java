package com.qoobot.qoochain.common.util;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Serial Number generator for QooBot robots.
 * Format: QB-{MODEL}-{YYYY}-{MMDD}-{SEQ}
 * Example: QB-PRO-2026-0628-0001
 */
public class SerialNumberGenerator {

    private static final DateTimeFormatter DATE_FMT = DateTimeFormatter.ofPattern("MMdd");
    private final String prefix;
    private final String model;
    private final AtomicLong sequence;

    public SerialNumberGenerator(String model, long startSequence) {
        this.model = model;
        this.prefix = "QB-" + model + "-";
        this.sequence = new AtomicLong(startSequence);
    }

    public String next() {
        LocalDate today = LocalDate.now();
        String datePart = today.getYear() + "-" + today.format(DATE_FMT);
        long seq = sequence.getAndIncrement();
        return String.format("%s%s-%04d", prefix, datePart, seq);
    }

    public String next(int year, int month, int day) {
        String datePart = String.format("%04d-%02d%02d", year, month, day);
        long seq = sequence.getAndIncrement();
        return String.format("%s%s-%04d", prefix, datePart, seq);
    }
}
