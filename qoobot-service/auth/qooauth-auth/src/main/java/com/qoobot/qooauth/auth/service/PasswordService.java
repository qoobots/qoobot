package com.qoobot.qooauth.auth.service;

import de.mkammerer.argon2.Argon2;
import de.mkammerer.argon2.Argon2Factory;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.util.Base64;

/**
 * Password hashing and verification using Argon2id.
 * Uses the argon2-jvm library with parameters:
 *   - iterations: 3
 *   - memory: 65536 KiB (64 MiB)
 *   - parallelism: 4
 *   - salt length: 16 bytes
 *   - hash length: 32 bytes
 */
@Service
public class PasswordService {

    private static final int ITERATIONS = 3;
    private static final int MEMORY = 65536;
    private static final int PARALLELISM = 4;
    private static final int SALT_LENGTH = 16;
    private static final int HASH_LENGTH = 32;

    private final Argon2 argon2 = Argon2Factory.create(
            Argon2Factory.Argon2Types.ARGON2id, SALT_LENGTH, HASH_LENGTH);
    private final SecureRandom random = new SecureRandom();

    /**
     * Hash a password with Argon2id and return the encoded hash string.
     * The output includes the salt and parameters.
     */
    public String hash(String password) {
        return argon2.hash(ITERATIONS, MEMORY, PARALLELISM, password.toCharArray());
    }

    /**
     * Verify a password against an Argon2id hash.
     */
    public boolean verify(String hash, String password) {
        return argon2.verify(hash, password.toCharArray());
    }

    /**
     * Generate a secure random salt for additional per-user salting if needed.
     */
    public String generateSalt() {
        byte[] salt = new byte[32];
        random.nextBytes(salt);
        return Base64.getEncoder().encodeToString(salt);
    }
}
