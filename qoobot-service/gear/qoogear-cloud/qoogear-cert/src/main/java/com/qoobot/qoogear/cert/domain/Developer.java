package com.qoobot.qoogear.cert.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.ZonedDateTime;

@Data
@Entity
@Table(name = "developers")
@EqualsAndHashCode(callSuper = true)
public class Developer extends BaseEntity {

    @Column(name = "user_id", nullable = false, unique = true)
    private Long userId;

    @Column(name = "company_name", nullable = false, length = 200)
    private String companyName;

    @Column(name = "contact_name", nullable = false, length = 100)
    private String contactName;

    @Column(name = "contact_email", nullable = false, length = 255)
    private String contactEmail;

    @Column(name = "contact_phone", length = 50)
    private String contactPhone;

    @Column(length = 500)
    private String website;

    @Column(length = 100)
    private String country;

    @Column(name = "business_license", length = 500)
    private String businessLicense;

    @Column(name = "verified_at")
    private ZonedDateTime verifiedAt;

    @Column(name = "verification_status", length = 20)
    private String verificationStatus = "pending";
}
