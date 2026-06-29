package com.qoobot.qooauth.audit.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "audit_integrity_chain")
public class AuditIntegrityChain {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "bucket_start", nullable = false)
    private Instant bucketStart;

    @Column(name = "bucket_end", nullable = false)
    private Instant bucketEnd;

    @Column(name = "merkle_root", nullable = false, length = 128)
    private String merkleRoot;

    @Column(name = "event_count", nullable = false)
    @Builder.Default
    private Integer eventCount = 0;

    @Column(name = "prev_chain_hash", length = 128)
    private String prevChainHash;

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

    @Column(name = "verified_at")
    private Instant verifiedAt;

    @Column(name = "verified_by", length = 64)
    private String verifiedBy;
}
