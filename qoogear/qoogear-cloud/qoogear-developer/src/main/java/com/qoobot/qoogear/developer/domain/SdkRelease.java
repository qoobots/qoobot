package com.qoobot.qoogear.developer.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.ZonedDateTime;

@Data
@Entity
@Table(name = "sdk_releases")
@EqualsAndHashCode(callSuper = true)
public class SdkRelease extends BaseEntity {

    @Column(nullable = false, length = 20)
    private String platform;

    @Column(nullable = false, length = 20)
    private String version;

    @Column(name = "download_url", nullable = false, length = 500)
    private String downloadUrl;

    @Column(name = "file_size")
    private Long fileSize;

    @Column(name = "checksum_sha256", length = 64)
    private String checksumSha256;

    @Column(name = "release_notes", columnDefinition = "TEXT")
    private String releaseNotes;

    @Column(name = "is_latest")
    private Boolean isLatest = false;

    @Column(name = "released_at", nullable = false)
    private ZonedDateTime releasedAt;
}
