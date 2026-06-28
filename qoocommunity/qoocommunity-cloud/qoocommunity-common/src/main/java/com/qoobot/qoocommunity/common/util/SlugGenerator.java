package com.qoobot.qoocommunity.common.util;

import java.text.Normalizer;
import java.util.Locale;
import java.util.regex.Pattern;

public class SlugGenerator {

    private static final Pattern NON_LATIN = Pattern.compile("[^\\w-]");
    private static final Pattern WHITESPACE = Pattern.compile("[\\s]+");
    private static final Pattern DASH = Pattern.compile("[-]+");

    public static String toSlug(String input) {
        if (input == null) return "";
        String normalized = Normalizer.normalize(input, Normalizer.Form.NFD);
        String noWhitespace = WHITESPACE.matcher(normalized.trim()).replaceAll("-");
        String slug = NON_LATIN.matcher(noWhitespace).replaceAll("");
        return DASH.matcher(slug).replaceAll("-").toLowerCase(Locale.ENGLISH);
    }
}
