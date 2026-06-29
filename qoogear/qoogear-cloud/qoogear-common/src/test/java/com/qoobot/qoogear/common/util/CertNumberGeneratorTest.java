package com.qoobot.qoogear.common.util;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for CertNumberGenerator and SpecNumberGenerator.
 */
class CertNumberGeneratorTest {

    @Test
    void shouldGenerateCertNumberForBasic() {
        String number = CertNumberGenerator.generateForLevel("basic");
        assertNotNull(number);
        assertTrue(number.startsWith("MFQ-"));
        assertTrue(number.contains("BASIC"));
    }

    @Test
    void shouldGenerateCertNumberForPremium() {
        String number = CertNumberGenerator.generateForLevel("premium");
        assertTrue(number.contains("PREMIUM"));
    }

    @Test
    void shouldGenerateCertNumberForPro() {
        String number = CertNumberGenerator.generateForLevel("pro");
        assertTrue(number.contains("PRO"));
    }

    @Test
    void shouldGenerateUniqueCertNumbers() {
        String n1 = CertNumberGenerator.generateForLevel("premium");
        String n2 = CertNumberGenerator.generateForLevel("premium");
        assertNotEquals(n1, n2, "Certificate numbers should be unique");
    }

    @Test
    void shouldGenerateSpecNumber() {
        String number = SpecNumberGenerator.generate("GRIPPER");
        assertNotNull(number);
        assertTrue(number.startsWith("MFQ-SPEC-"));
    }

    @Test
    void shouldGenerateUniqueSpecNumbers() {
        String n1 = SpecNumberGenerator.generate("SENSOR");
        String n2 = SpecNumberGenerator.generate("SENSOR");
        assertNotEquals(n1, n2, "Spec numbers should be unique");
    }
}
