package com.qoobot.qooauth.auth.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import javax.crypto.Cipher;
import javax.crypto.KeyAgreement;
import javax.crypto.Mac;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.spec.X509EncodedKeySpec;
import java.util.Arrays;
import java.util.Base64;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * End-to-End Encryption (E2EE) Service.
 * <p>
 * Implements X3DH (Extended Triple Diffie-Hellman) for key agreement and
 * Double Ratchet for forward-secure message encryption.
 * <p>
 * Protocol Overview:
 * <ol>
 *   <li><b>X3DH Key Agreement</b> — Establish shared secret between two parties
 *       using identity keys + ephemeral keys + pre-keys</li>
 *   <li><b>Double Ratchet</b> — Per-message key derivation with forward secrecy:
 *       <ul>
 *         <li>DH Ratchet: Rotate key pair on each message</li>
 *         <li>Symmetric Ratchet: Derive message keys via HKDF chain</li>
 *       </ul>
 *   </li>
 * </ol>
 * <p>
 * Key Types:
 * <ul>
 *   <li>IK (Identity Key) — Long-term Ed25519 key pair</li>
 *   <li>EK (Ephemeral Key) — Per-session X25519 key pair</li>
 *   <li>SPK (Signed Pre-Key) — Medium-term X25519 key, signed by IK</li>
 *   <li>OPK (One-time Pre-Key) — Single-use X25519 key</li>
 * </ul>
 */
@Service
public class E2EEncryptionService {

    private static final Logger log = LoggerFactory.getLogger(E2EEncryptionService.class);

    // Algorithm constants
    private static final String ECDH_ALGORITHM = "X25519";
    private static final String SIGN_ALGORITHM = "Ed25519";
    private static final String AES_ALGORITHM = "AES/GCM/NoPadding";
    private static final String HKDF_ALGORITHM = "HmacSHA256";
    private static final int AES_KEY_SIZE = 256;
    private static final int GCM_IV_LENGTH = 12;
    private static final int GCM_TAG_LENGTH = 128;

    // In-memory key store (production would use HSM/secure storage)
    private final Map<String, KeyBundle> keyStore = new ConcurrentHashMap<>();
    private final Map<String, RatchetState> ratchetStates = new ConcurrentHashMap<>();

    /**
     * Generate a new identity key pair for a user.
     */
    public KeyPair generateIdentityKeyPair() throws NoSuchAlgorithmException, InvalidAlgorithmParameterException {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance(ECDH_ALGORITHM);
        return keyGen.generateKeyPair();
    }

    /**
     * Generate a signed pre-key pair.
     */
    public SignedPreKey generateSignedPreKey(PrivateKey identityKey) throws Exception {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance(ECDH_ALGORITHM);
        KeyPair preKeyPair = keyGen.generateKeyPair();

        // Sign the pre-key public key with identity key
        Signature sig = Signature.getInstance(SIGN_ALGORITHM);
        sig.initSign(identityKey);
        sig.update(preKeyPair.getPublic().getEncoded());
        byte[] signature = sig.sign();

        return new SignedPreKey(preKeyPair, signature);
    }

    /**
     * Generate a one-time pre-key pair.
     */
    public KeyPair generateOneTimePreKey() throws NoSuchAlgorithmException, InvalidAlgorithmParameterException {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance(ECDH_ALGORITHM);
        return keyGen.generateKeyPair();
    }

    /**
     * Register a user's key bundle for X3DH.
     */
    public void registerKeyBundle(String userId, KeyBundle bundle) {
        keyStore.put(userId, bundle);
        log.info("Registered key bundle for user {}", userId);
    }

    /**
     * Perform X3DH key agreement to establish a shared secret with a peer.
     *
     * @param initiatorUserId   the initiator's user ID
     * @param initiatorIK       initiator's identity key pair
     * @param initiatorEK       initiator's ephemeral key pair
     * @param responderUserId   the responder's user ID
     * @param responderBundle   responder's key bundle (IK public + SPK + OPK)
     * @return shared secret and initial ratchet state
     */
    public X3DHResult performX3DH(String initiatorUserId, KeyPair initiatorIK,
                                   KeyPair initiatorEK, String responderUserId,
                                   KeyBundle responderBundle) throws Exception {
        KeyAgreement ka = KeyAgreement.getInstance(ECDH_ALGORITHM);

        // DH1 = DH(IK_A, SPK_B)
        ka.init(initiatorIK.getPrivate());
        ka.doPhase(responderBundle.signedPreKey.getPublic(), true);
        byte[] dh1 = ka.generateSecret();

        // DH2 = DH(EK_A, IK_B)
        ka.init(initiatorEK.getPrivate());
        ka.doPhase(responderBundle.identityKey, true);
        byte[] dh2 = ka.generateSecret();

        // DH3 = DH(EK_A, SPK_B)
        ka.init(initiatorEK.getPrivate());
        ka.doPhase(responderBundle.signedPreKey.getPublic(), true);
        byte[] dh3 = ka.generateSecret();

        // DH4 = DH(EK_A, OPK_B) — optional, if OPK is available
        byte[] dh4 = new byte[32];
        if (responderBundle.oneTimePreKey != null) {
            ka.init(initiatorEK.getPrivate());
            ka.doPhase(responderBundle.oneTimePreKey, true);
            dh4 = ka.generateSecret();
        }

        // Combine all DH outputs: SK = HKDF(DH1 || DH2 || DH3 || DH4)
        byte[] combined = ByteBuffer.allocate(dh1.length + dh2.length + dh3.length + dh4.length)
                .put(dh1).put(dh2).put(dh3).put(dh4).array();

        byte[] sharedSecret = hkdf(combined, "QooBot_X3DH_v1".getBytes(StandardCharsets.UTF_8), 32);

        // Initialize ratchet state
        RatchetState state = new RatchetState(
                sharedSecret,
                responderBundle.signedPreKey.getPublic(),
                initiatorEK
        );
        ratchetStates.put(initiatorUserId + ":" + responderUserId, state);

        return new X3DHResult(sharedSecret, initiatorEK.getPublic());
    }

    /**
     * Encrypt a message using Double Ratchet.
     *
     * @param senderId      sender user ID
     * @param receiverId    receiver user ID
     * @param plaintext     the plaintext message bytes
     * @return encrypted message with metadata
     */
    public RatchetMessage encrypt(String senderId, String receiverId, byte[] plaintext) throws Exception {
        String stateKey = senderId + ":" + receiverId;
        RatchetState state = ratchetStates.get(stateKey);
        if (state == null) {
            throw new IllegalStateException("No ratchet state established. Perform X3DH first.");
        }

        // Perform DH ratchet step
        KeyAgreement ka = KeyAgreement.getInstance(ECDH_ALGORITHM);
        ka.init(state.dhKeyPair.getPrivate());
        ka.doPhase(state.peerPublicKey, true);
        byte[] dhOutput = ka.generateSecret();

        // Derive new root key and chain key via HKDF
        byte[] combined = ByteBuffer.allocate(state.rootKey.length + dhOutput.length)
                .put(state.rootKey).put(dhOutput).array();
        byte[] derived = hkdf(combined, "QooBot_DoubleRatchet_v1".getBytes(StandardCharsets.UTF_8), 64);

        byte[] newRootKey = Arrays.copyOfRange(derived, 0, 32);
        byte[] chainKey = Arrays.copyOfRange(derived, 32, 64);

        // Derive message key from chain key
        byte[] messageKey = hkdf(chainKey, "QooBot_MessageKey_v1".getBytes(StandardCharsets.UTF_8), 32);

        // Encrypt with AES-256-GCM
        byte[] iv = generateIV();
        Cipher cipher = Cipher.getInstance(AES_ALGORITHM);
        SecretKeySpec keySpec = new SecretKeySpec(messageKey, "AES");
        GCMParameterSpec gcmSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
        cipher.init(Cipher.ENCRYPT_MODE, keySpec, gcmSpec);
        byte[] ciphertext = cipher.doFinal(plaintext);

        // Update ratchet state (symmetric ratchet: advance chain key)
        byte[] newChainKey = hkdf(chainKey, "QooBot_ChainAdvance_v1".getBytes(StandardCharsets.UTF_8), 32);
        state.rootKey = newRootKey;
        state.chainKey = newChainKey;
        state.messageCount++;

        return new RatchetMessage(ciphertext, iv, state.dhKeyPair.getPublic(), state.messageCount);
    }

    /**
     * Decrypt a message using Double Ratchet.
     *
     * @param senderId    sender user ID
     * @param receiverId  receiver user ID
     * @param message     the encrypted ratchet message
     * @return decrypted plaintext bytes
     */
    public byte[] decrypt(String senderId, String receiverId, RatchetMessage message) throws Exception {
        String stateKey = receiverId + ":" + senderId;
        RatchetState state = ratchetStates.get(stateKey);
        if (state == null) {
            throw new IllegalStateException("No ratchet state established. Perform X3DH first.");
        }

        // DH ratchet step with sender's public key
        KeyAgreement ka = KeyAgreement.getInstance(ECDH_ALGORITHM);
        ka.init(state.dhKeyPair.getPrivate());
        ka.doPhase(message.senderPublicKey, true);
        byte[] dhOutput = ka.generateSecret();

        byte[] combined = ByteBuffer.allocate(state.rootKey.length + dhOutput.length)
                .put(state.rootKey).put(dhOutput).array();
        byte[] derived = hkdf(combined, "QooBot_DoubleRatchet_v1".getBytes(StandardCharsets.UTF_8), 64);

        byte[] newRootKey = Arrays.copyOfRange(derived, 0, 32);
        byte[] chainKey = Arrays.copyOfRange(derived, 32, 64);

        // Derive message key
        byte[] messageKey = hkdf(chainKey, "QooBot_MessageKey_v1".getBytes(StandardCharsets.UTF_8), 32);

        // Decrypt with AES-256-GCM
        Cipher cipher = Cipher.getInstance(AES_ALGORITHM);
        SecretKeySpec keySpec = new SecretKeySpec(messageKey, "AES");
        GCMParameterSpec gcmSpec = new GCMParameterSpec(GCM_TAG_LENGTH, message.iv);
        cipher.init(Cipher.DECRYPT_MODE, keySpec, gcmSpec);
        byte[] plaintext = cipher.doFinal(message.ciphertext);

        // Advance ratchet
        byte[] newChainKey = hkdf(chainKey, "QooBot_ChainAdvance_v1".getBytes(StandardCharsets.UTF_8), 32);
        state.rootKey = newRootKey;
        state.chainKey = newChainKey;
        state.peerPublicKey = message.senderPublicKey;
        state.messageCount++;

        return plaintext;
    }

    /**
     * Encrypt a string message (convenience method).
     */
    public RatchetMessage encryptString(String senderId, String receiverId, String plaintext) throws Exception {
        return encrypt(senderId, receiverId, plaintext.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * Decrypt to string (convenience method).
     */
    public String decryptString(String senderId, String receiverId, RatchetMessage message) throws Exception {
        return new String(decrypt(senderId, receiverId, message), StandardCharsets.UTF_8);
    }

    /**
     * Delete ratchet state (for session cleanup).
     */
    public void deleteSession(String senderId, String receiverId) {
        ratchetStates.remove(senderId + ":" + receiverId);
        ratchetStates.remove(receiverId + ":" + senderId);
    }

    /**
     * Generate a session key for symmetric E2EE communication.
     * Used for bulk data encryption after X3DH handshake.
     */
    public SecretKey generateSessionKey() throws NoSuchAlgorithmException {
        KeyGenerator keyGen = KeyGenerator.getInstance("AES");
        keyGen.init(AES_KEY_SIZE);
        return keyGen.generateKey();
    }

    /**
     * Encrypt data with a session key using AES-256-GCM.
     */
    public byte[] encryptWithKey(SecretKey key, byte[] plaintext, byte[] iv) throws Exception {
        Cipher cipher = Cipher.getInstance(AES_ALGORITHM);
        GCMParameterSpec gcmSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
        cipher.init(Cipher.ENCRYPT_MODE, key, gcmSpec);
        return cipher.doFinal(plaintext);
    }

    /**
     * Decrypt data with a session key using AES-256-GCM.
     */
    public byte[] decryptWithKey(SecretKey key, byte[] ciphertext, byte[] iv) throws Exception {
        Cipher cipher = Cipher.getInstance(AES_ALGORITHM);
        GCMParameterSpec gcmSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
        cipher.init(Cipher.DECRYPT_MODE, key, gcmSpec);
        return cipher.doFinal(ciphertext);
    }

    /**
     * Sign data with Ed25519 private key.
     */
    public byte[] sign(PrivateKey privateKey, byte[] data) throws Exception {
        Signature sig = Signature.getInstance(SIGN_ALGORITHM);
        sig.initSign(privateKey);
        sig.update(data);
        return sig.sign();
    }

    /**
     * Verify signature with Ed25519 public key.
     */
    public boolean verify(PublicKey publicKey, byte[] data, byte[] signature) throws Exception {
        Signature sig = Signature.getInstance(SIGN_ALGORITHM);
        sig.initVerify(publicKey);
        sig.update(data);
        return sig.verify(signature);
    }

    // ========================================================================
    // Crypto Helpers
    // ========================================================================

    /**
     * HKDF key derivation using HMAC-SHA256.
     */
    private byte[] hkdf(byte[] inputKeyMaterial, byte[] info, int length) throws Exception {
        // Extract
        Mac mac = Mac.getInstance(HKDF_ALGORITHM);
        mac.init(new SecretKeySpec(new byte[32], HKDF_ALGORITHM)); // Salt = zeros
        byte[] prk = mac.doFinal(inputKeyMaterial);

        // Expand
        mac.init(new SecretKeySpec(prk, HKDF_ALGORITHM));
        ByteBuffer buffer = ByteBuffer.allocate(info.length + 1);
        buffer.put(info);
        buffer.put((byte) 0x01);
        byte[] result = mac.doFinal(buffer.array());

        if (result.length < length) {
            // Multi-block expansion for longer outputs
            byte[] t = result;
            int offset = 0;
            byte[] fullResult = new byte[length];
            for (int i = 1; offset < length; i++) {
                mac.init(new SecretKeySpec(prk, HKDF_ALGORITHM));
                mac.update(t);
                mac.update(info);
                mac.update((byte) i);
                t = mac.doFinal();
                int copyLen = Math.min(t.length, length - offset);
                System.arraycopy(t, 0, fullResult, offset, copyLen);
                offset += copyLen;
            }
            return fullResult;
        }

        return Arrays.copyOf(result, length);
    }

    private byte[] generateIV() {
        byte[] iv = new byte[GCM_IV_LENGTH];
        new SecureRandom().nextBytes(iv);
        return iv;
    }

    // ========================================================================
    // Data Classes
    // ========================================================================

    /**
     * X3DH key bundle for a user.
     */
    public static class KeyBundle {
        public final PublicKey identityKey;
        public final SignedPreKey signedPreKey;
        public final PublicKey oneTimePreKey; // nullable
        public final int signedPreKeyId;
        public final int oneTimePreKeyId;

        public KeyBundle(PublicKey identityKey, SignedPreKey signedPreKey,
                          PublicKey oneTimePreKey, int signedPreKeyId, int oneTimePreKeyId) {
            this.identityKey = identityKey;
            this.signedPreKey = signedPreKey;
            this.oneTimePreKey = oneTimePreKey;
            this.signedPreKeyId = signedPreKeyId;
            this.oneTimePreKeyId = oneTimePreKeyId;
        }
    }

    /**
     * Signed pre-key with its signature.
     */
    public static class SignedPreKey {
        public final KeyPair keyPair;
        public final byte[] signature;

        public SignedPreKey(KeyPair keyPair, byte[] signature) {
            this.keyPair = keyPair;
            this.signature = signature;
        }

        public PublicKey getPublic() { return keyPair.getPublic(); }
        public PrivateKey getPrivate() { return keyPair.getPrivate(); }
    }

    /**
     * Result of X3DH key agreement.
     */
    public static class X3DHResult {
        public final byte[] sharedSecret;
        public final PublicKey ephemeralPublicKey;

        public X3DHResult(byte[] sharedSecret, PublicKey ephemeralPublicKey) {
            this.sharedSecret = sharedSecret;
            this.ephemeralPublicKey = ephemeralPublicKey;
        }
    }

    /**
     * Double Ratchet state.
     */
    private static class RatchetState {
        byte[] rootKey;
        byte[] chainKey;
        PublicKey peerPublicKey;
        KeyPair dhKeyPair;
        int messageCount;

        RatchetState(byte[] rootKey, PublicKey peerPublicKey, KeyPair dhKeyPair) {
            this.rootKey = rootKey;
            this.chainKey = new byte[32];
            this.peerPublicKey = peerPublicKey;
            this.dhKeyPair = dhKeyPair;
            this.messageCount = 0;
        }
    }

    /**
     * Encrypted message with Double Ratchet metadata.
     */
    public static class RatchetMessage {
        public final byte[] ciphertext;
        public final byte[] iv;
        public final PublicKey senderPublicKey;
        public final int messageNumber;

        public RatchetMessage(byte[] ciphertext, byte[] iv, PublicKey senderPublicKey, int messageNumber) {
            this.ciphertext = ciphertext;
            this.iv = iv;
            this.senderPublicKey = senderPublicKey;
            this.messageNumber = messageNumber;
        }

        /**
         * Serialize to Base64 for transport.
         */
        public String toBase64() {
            byte[] pubKeyBytes = senderPublicKey.getEncoded();
            ByteBuffer buf = ByteBuffer.allocate(4 + ciphertext.length + iv.length + 4 + pubKeyBytes.length + 4);
            buf.putInt(ciphertext.length);
            buf.put(ciphertext);
            buf.put(iv);
            buf.putInt(pubKeyBytes.length);
            buf.put(pubKeyBytes);
            buf.putInt(messageNumber);
            return Base64.getEncoder().encodeToString(buf.array());
        }

        /**
         * Deserialize from Base64.
         */
        public static RatchetMessage fromBase64(String encoded) throws Exception {
            byte[] data = Base64.getDecoder().decode(encoded);
            ByteBuffer buf = ByteBuffer.wrap(data);

            int ctLen = buf.getInt();
            byte[] ct = new byte[ctLen];
            buf.get(ct);

            byte[] iv = new byte[GCM_IV_LENGTH];
            buf.get(iv);

            int pkLen = buf.getInt();
            byte[] pkBytes = new byte[pkLen];
            buf.get(pkBytes);

            int msgNum = buf.getInt();

            KeyFactory kf = KeyFactory.getInstance(ECDH_ALGORITHM);
            PublicKey pk = kf.generatePublic(new X509EncodedKeySpec(pkBytes));

            return new RatchetMessage(ct, iv, pk, msgNum);
        }
    }
}
