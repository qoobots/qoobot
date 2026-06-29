package com.qoobot.qoogear.lab.repository;

import com.qoobot.qoogear.lab.domain.LabEquipment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.time.ZonedDateTime;
import java.util.List;

@Repository
public interface LabEquipmentRepository extends JpaRepository<LabEquipment, Long> {
    List<LabEquipment> findByLaboratoryId(Long laboratoryId);

    @Query("SELECT e FROM LabEquipment e WHERE e.nextCalibrationDue < :date AND e.status = 'active'")
    List<LabEquipment> findNeedingCalibration(@Param("date") ZonedDateTime date);
}
