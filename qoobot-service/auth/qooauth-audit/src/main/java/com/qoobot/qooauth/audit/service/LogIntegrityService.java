package com.qoobot.qooauth.audit.service;

import com.qoobot.qooauth.audit.entity.AuditIntegrityChain;
import com.qoobot.qooauth.audit.entity.AuditLog;
import com.qoobot.qooauth.audit.repository.AuditIntegrityChainRepository;
import com.qoobot.qooauth.audit.repository.AuditLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;

/**
 * Merkle-tree based audit log integrity chain.
 * <p>
 * Every hour, computes a Merkle root of all audit events in the past hour
 * and chains it to the previous hour's hash, creating an immutable,
 * tamper-evident chain (blockchain-like without the consensus).
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class LogIntegrityService {

    private final AuditLogRepository auditLogRepository;
    private final AuditIntegrityChainRepository integrityChainRepository;

    /**
     * Scheduled job: every hour, compute Merkle root for the previous hour's events.
     */
    @Scheduled(cron = "0 5 * * * *") // At minute 5 of every hour
    @Transactional
    public void buildIntegrityChain() {
        Instant now = Instant.now().truncatedTo(ChronoUnit.HOURS);
        Instant bucketEnd = now;
        Instant bucketStart = now.minus(1, ChronoUnit.HOURS);

        // Check if already computed
        if (integrityChainRepository.findByBucketStartAndBucketEnd(bucketStart, bucketEnd).isPresent()) {
            log.debug("Integrity chain already exists for bucket: {} - {}", bucketStart, bucketEnd);
            return;
        }

        List<AuditLog> events = auditLogRepository.findEventsInBucket(bucketStart, bucketEnd);
        if (events.isEmpty()) {
            log.debug("No audit events in bucket: {} - {}", bucketStart, bucketEnd);
            return;
        }

        String merkleRoot = computeMerkleRoot(events);
        String prevChainHash = integrityChainRepository.findTopByOrderByBucketEndDesc()
                .map(AuditIntegrityChain::getMerkleRoot)
                .orElse("0".repeat(64));

        AuditIntegrityChain chain = AuditIntegrityChain.builder()
                .bucketStart(bucketStart)
                .bucketEnd(bucketEnd)
                .merkleRoot(merkleRoot)
                .eventCount(events.size())
                .prevChainHash(prevChainHash)
                .build();

        integrityChainRepository.save(chain);
        log.info("Built integrity chain: bucket={}-{}, events={}, merkleRoot={}",
                bucketStart, bucketEnd, events.size(), merkleRoot.substring(0, 16));
    }

    /**
     * Verify the integrity chain for a given time range.
     *
     * @return true if all chain links are valid
     */
    @Transactional(readOnly = true)
    public boolean verifyChainIntegrity(Instant start, Instant end) {
        List<AuditIntegrityChain> chain = integrityChainRepository.findChainInRange(start, end);
        if (chain.isEmpty()) return true;

        for (int i = 1; i < chain.size(); i++) {
            String expectedPrev = chain.get(i - 1).getMerkleRoot();
            String actualPrev = chain.get(i).getPrevChainHash();
            if (!expectedPrev.equals(actualPrev)) {
                log.error("Integrity chain broken at bucket: {} - {}", chain.get(i).getBucketStart(), chain.get(i).getBucketEnd());
                return false;
            }
        }

        // Verify each bucket's Merkle root against actual events
        for (AuditIntegrityChain link : chain) {
            List<AuditLog> events = auditLogRepository.findEventsInBucket(link.getBucketStart(), link.getBucketEnd());
            String computedRoot = computeMerkleRoot(events);
            if (!computedRoot.equals(link.getMerkleRoot())) {
                log.error("Merkle root mismatch at bucket: {} - {}. Expected: {}, Actual: {}",
                        link.getBucketStart(), link.getBucketEnd(),
                        link.getMerkleRoot().substring(0, 16), computedRoot.substring(0, 16));
                return false;
            }
        }

        return true;
    }

    /**
     * Compute Merkle root from a list of audit events.
     * Leaf hash = SHA-256(event_id + integrity_hash)
     * Then pairwise hash until root.
     */
    String computeMerkleRoot(List<AuditLog> events) {
        if (events.isEmpty()) return "0".repeat(64);

        // Compute leaf hashes
        List<String> hashes = events.stream()
                .map(e -> sha256(e.getEventId().toString() + e.getIntegrityHash()))
                .toList();

        // Build tree bottom-up
        List<String> current = hashes;
        while (current.size() > 1) {
            int size = current.size();
            java.util.List<String> next = new java.util.ArrayList<>((size + 1) / 2);
            for (int i = 0; i < size; i += 2) {
                if (i + 1 < size) {
                    next.add(sha256(current.get(i) + current.get(i + 1)));
                } else {
                    // Odd node: hash with itself
                    next.add(sha256(current.get(i) + current.get(i)));
                }
            }
            current = next;
        }

        return current.get(0);
    }

    private String sha256(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(input.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }
}
