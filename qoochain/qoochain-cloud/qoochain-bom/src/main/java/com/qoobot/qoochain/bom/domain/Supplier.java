package com.qoobot.qoochain.bom.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDate;

@Entity
@Table(name = "supplier")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class Supplier extends BaseEntity {

    @Column(name = "supplier_code", nullable = false, unique = true, length = 64)
    private String supplierCode;

    @Column(name = "supplier_name", nullable = false, length = 128)
    private String supplierName;

    @Column(nullable = false, length = 32)
    private String category;

    @Column(length = 64)
    private String country;

    @Column(nullable = false)
    private int rating = 3;

    @Column(nullable = false, length = 16)
    @Enumerated(EnumType.STRING)
    private SupplierStatus status = SupplierStatus.QUALIFIED;

    @Column(name = "contact_name", length = 64)
    private String contactName;

    @Column(name = "contact_email", length = 128)
    private String contactEmail;

    @Column(name = "contact_phone", length = 32)
    private String contactPhone;

    @Column(name = "audit_date")
    private LocalDate auditDate;

    @Column(name = "audit_report_url", length = 512)
    private String auditReportUrl;

    public enum SupplierStatus { TRIAL, QUALIFIED, PROBATION, DISQUALIFIED }
}
