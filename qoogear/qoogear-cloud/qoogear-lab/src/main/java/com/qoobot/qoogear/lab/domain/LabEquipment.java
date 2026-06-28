package com.qoobot.qoogear.lab.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.ZonedDateTime;

@Data
@Entity
@Table(name = "lab_equipment")
@EqualsAndHashCode(callSuper = true)
public class LabEquipment extends BaseEntity {

    @Column(name = "laboratory_id", nullable = false)
    private Long laboratoryId;

    @Column(nullable = false, length = 200)
    private String name;

    @Column(length = 100)
    private String model;

    @Column(name = "serial_number", nullable = false, length = 100)
    private String serialNumber;

    @Column(name = "equipment_type", nullable = false, length = 50)
    private String equipmentType;

    @Column(name = "calibrated_at")
    private ZonedDateTime calibratedAt;

    @Column(name = "next_calibration_due")
    private ZonedDateTime nextCalibrationDue;

    @Column(nullable = false, length = 20)
    private String status = "active";
}
