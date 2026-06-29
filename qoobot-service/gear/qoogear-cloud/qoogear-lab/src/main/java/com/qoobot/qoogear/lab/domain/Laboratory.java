package com.qoobot.qoogear.lab.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.util.List;

@Data
@Entity
@Table(name = "laboratories")
@EqualsAndHashCode(callSuper = true)
public class Laboratory extends BaseEntity {

    @Column(nullable = false, length = 200)
    private String name;

    @Column(name = "lab_code", nullable = false, unique = true, length = 50)
    private String labCode;

    @Column(nullable = false, length = 100)
    private String country;

    @Column(length = 100)
    private String city;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String address;

    @Column(name = "contact_name", nullable = false, length = 100)
    private String contactName;

    @Column(name = "contact_email", nullable = false, length = 255)
    private String contactEmail;

    @Column(name = "contact_phone", length = 50)
    private String contactPhone;

    @Column(length = 200)
    private String accreditation;

    @Column(columnDefinition = "varchar(100)[]")
    private List<String> scope;

    @Column(nullable = false, length = 20)
    private String status = "active";
}
