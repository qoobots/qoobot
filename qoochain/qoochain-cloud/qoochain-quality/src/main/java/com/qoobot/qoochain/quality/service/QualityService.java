package com.qoobot.qoochain.quality.service;

import com.qoobot.qoochain.common.exception.QooChainException;
import com.qoobot.qoochain.quality.domain.*;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class QualityService {

    @PersistenceContext
    private EntityManager em;

    @Transactional
    public InspectionRecord createInspection(InspectionRecord record) {
        em.persist(record);
        return record;
    }

    @Transactional
    public InspectionMeasurement addMeasurement(Long inspectionId, InspectionMeasurement measurement) {
        InspectionRecord inspection = em.find(InspectionRecord.class, inspectionId);
        if (inspection == null) throw QooChainException.notFound("InspectionRecord", inspectionId.toString());
        measurement.setInspection(inspection);
        measurement.setResult(isPassing(measurement) ? "PASS" : "FAIL");
        em.persist(measurement);
        return measurement;
    }

    @Transactional
    public InspectionRecord finalizeInspection(Long inspectionId) {
        InspectionRecord inspection = em.find(InspectionRecord.class, inspectionId);
        if (inspection == null) throw QooChainException.notFound("InspectionRecord", inspectionId.toString());
        List<InspectionMeasurement> measurements = em.createQuery(
            "SELECT m FROM InspectionMeasurement m WHERE m.inspection.id = :inspId", InspectionMeasurement.class)
            .setParameter("inspId", inspectionId).getResultList();
        boolean anyFail = measurements.stream().anyMatch(m -> "FAIL".equals(m.getResult()));
        inspection.setOverallResult(anyFail ? "FAIL" : "PASS");
        inspection.setDefectCount((int) measurements.stream().filter(m -> "FAIL".equals(m.getResult())).count());
        return em.merge(inspection);
    }

    @Transactional(readOnly = true)
    public List<InspectionRecord> getInspectionsByRobot(Long robotId) {
        return em.createQuery(
            "SELECT i FROM InspectionRecord i WHERE i.robotId = :robotId ORDER BY i.inspectedAt DESC",
            InspectionRecord.class).setParameter("robotId", robotId).getResultList();
    }

    @Transactional(readOnly = true)
    public List<InspectionRecord> getInspectionsByType(String inspectionType) {
        return em.createQuery(
            "SELECT i FROM InspectionRecord i WHERE i.inspectionType = :type ORDER BY i.inspectedAt DESC",
            InspectionRecord.class).setParameter("type", inspectionType).getResultList();
    }

    @Transactional
    public BurnInTest startBurnIn(Long robotId, int durationHours) {
        BurnInTest test = new BurnInTest();
        test.setRobotId(robotId);
        test.setDurationHours(durationHours);
        em.persist(test);
        log.info("Started burn-in test for robot {} ({} hours)", robotId, durationHours);
        return test;
    }

    @Transactional
    public BurnInTest completeBurnIn(Long testId, boolean passed, String failureReason) {
        BurnInTest test = em.find(BurnInTest.class, testId);
        if (test == null) throw QooChainException.notFound("BurnInTest", testId.toString());
        test.setStatus(passed ? BurnInTest.BurnInStatus.PASSED : BurnInTest.BurnInStatus.FAILED);
        test.setCompletedAt(Instant.now());
        if (!passed) test.setFailureReason(failureReason);
        return em.merge(test);
    }

    @Transactional(readOnly = true)
    public List<BurnInTest> getBurnInTests(Long robotId) {
        return em.createQuery(
            "SELECT b FROM BurnInTest b WHERE b.robotId = :robotId ORDER BY b.startedAt DESC", BurnInTest.class)
            .setParameter("robotId", robotId).getResultList();
    }

    @Transactional
    public SpcStatistics calculateSpc(String measurementName, String stationCode, Instant periodStart, Instant periodEnd) {
        List<InspectionMeasurement> measurements = em.createQuery(
            "SELECT m FROM InspectionMeasurement m WHERE m.measurementName = :name " +
            "AND m.createdAt BETWEEN :start AND :end ORDER BY m.createdAt",
            InspectionMeasurement.class)
            .setParameter("name", measurementName)
            .setParameter("start", periodStart)
            .setParameter("end", periodEnd)
            .getResultList();

        if (measurements.isEmpty()) return null;

        int n = measurements.size();
        BigDecimal sum = measurements.stream().map(InspectionMeasurement::getValue).reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal mean = sum.divide(BigDecimal.valueOf(n), 4, RoundingMode.HALF_UP);

        BigDecimal variance = measurements.stream()
            .map(m -> m.getValue().subtract(mean).pow(2))
            .reduce(BigDecimal.ZERO, BigDecimal::add)
            .divide(BigDecimal.valueOf(n - 1), 8, RoundingMode.HALF_UP);
        BigDecimal stdDev = BigDecimal.valueOf(Math.sqrt(variance.doubleValue()));

        BigDecimal ucl = mean.add(stdDev.multiply(BigDecimal.valueOf(3)));
        BigDecimal lcl = mean.subtract(stdDev.multiply(BigDecimal.valueOf(3)));

        SpcStatistics spc = new SpcStatistics();
        spc.setMeasurementName(measurementName);
        spc.setStationCode(stationCode);
        spc.setPeriodStart(periodStart);
        spc.setPeriodEnd(periodEnd);
        spc.setSampleCount(n);
        spc.setMeanValue(mean);
        spc.setStdDev(stdDev);
        spc.setUcl(ucl);
        spc.setLcl(lcl);
        // Check if any point is out of control
        boolean outOfControl = measurements.stream().anyMatch(m ->
            m.getValue().compareTo(ucl) > 0 || m.getValue().compareTo(lcl) < 0);
        spc.setOutOfControl(outOfControl);
        em.persist(spc);
        return spc;
    }

    @Transactional(readOnly = true)
    public List<SpcStatistics> getSpcHistory(String measurementName) {
        return em.createQuery(
            "SELECT s FROM SpcStatistics s WHERE s.measurementName = :name ORDER BY s.periodStart DESC",
            SpcStatistics.class).setParameter("name", measurementName).getResultList();
    }

    private boolean isPassing(InspectionMeasurement measurement) {
        if (measurement.getSpecLower() == null || measurement.getSpecUpper() == null) return true;
        return measurement.getValue().compareTo(measurement.getSpecLower()) >= 0
            && measurement.getValue().compareTo(measurement.getSpecUpper()) <= 0;
    }
}
