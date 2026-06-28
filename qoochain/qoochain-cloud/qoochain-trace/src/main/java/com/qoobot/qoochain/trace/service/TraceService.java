package com.qoobot.qoochain.trace.service;

import com.qoobot.qoochain.common.exception.QooChainException;
import com.qoobot.qoochain.trace.domain.*;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class TraceService {

    @PersistenceContext
    private EntityManager em;

    @Transactional
    public Robot createRobot(Robot robot) {
        em.persist(robot);
        log.info("Created robot {}", robot.getSerialNumber());
        return robot;
    }

    @Transactional(readOnly = true)
    public Robot getRobot(Long id) {
        Robot robot = em.find(Robot.class, id);
        if (robot == null) throw QooChainException.notFound("Robot", id.toString());
        return robot;
    }

    @Transactional(readOnly = true)
    public Robot getBySerialNumber(String serialNumber) {
        List<Robot> robots = em.createQuery(
            "SELECT r FROM Robot r WHERE r.serialNumber = :sn", Robot.class)
            .setParameter("sn", serialNumber).getResultList();
        if (robots.isEmpty()) throw QooChainException.notFound("Robot", serialNumber);
        return robots.get(0);
    }

    @Transactional(readOnly = true)
    public List<Robot> listRobots() {
        return em.createQuery("SELECT r FROM Robot r ORDER BY r.createdAt DESC", Robot.class)
            .setMaxResults(100).getResultList();
    }

    @Transactional
    public AssemblyRecord recordAssembly(Long robotId, Long stationId, String operatorId) {
        Robot robot = em.find(Robot.class, robotId);
        if (robot == null) throw QooChainException.notFound("Robot", robotId.toString());
        AssemblyRecord record = new AssemblyRecord();
        record.setRobot(robot);
        record.setStationId(stationId);
        record.setOperatorId(operatorId);
        record.setStartedAt(Instant.now());
        em.persist(record);
        return record;
    }

    @Transactional
    public AssemblyRecord completeAssembly(Long recordId) {
        AssemblyRecord record = em.find(AssemblyRecord.class, recordId);
        if (record == null) throw QooChainException.notFound("AssemblyRecord", recordId.toString());
        record.setStatus("COMPLETED");
        record.setCompletedAt(Instant.now());
        return em.merge(record);
    }

    @Transactional(readOnly = true)
    public List<AssemblyRecord> getAssemblyRecords(Long robotId) {
        return em.createQuery(
            "SELECT a FROM AssemblyRecord a WHERE a.robot.id = :robotId ORDER BY a.startedAt",
            AssemblyRecord.class).setParameter("robotId", robotId).getResultList();
    }

    @Transactional
    public ComponentTrace recordComponent(Long robotId, Long materialId, String lotNumber, Long supplierId) {
        Robot robot = em.find(Robot.class, robotId);
        if (robot == null) throw QooChainException.notFound("Robot", robotId.toString());
        ComponentTrace trace = new ComponentTrace();
        trace.setRobot(robot);
        trace.setMaterialId(materialId);
        trace.setLotNumber(lotNumber);
        trace.setSupplierId(supplierId);
        em.persist(trace);
        return trace;
    }

    @Transactional(readOnly = true)
    public List<ComponentTrace> getComponentTraces(Long robotId) {
        return em.createQuery(
            "SELECT c FROM ComponentTrace c WHERE c.robot.id = :robotId", ComponentTrace.class)
            .setParameter("robotId", robotId).getResultList();
    }

    @Transactional(readOnly = true)
    public List<ComponentTrace> findByLotNumber(String lotNumber) {
        return em.createQuery(
            "SELECT c FROM ComponentTrace c WHERE c.lotNumber = :lot", ComponentTrace.class)
            .setParameter("lot", lotNumber).getResultList();
    }

    @Transactional
    public DigitalPassport issuePassport(Long robotId, Map<String, Object> passportData) {
        Robot robot = em.find(Robot.class, robotId);
        if (robot == null) throw QooChainException.notFound("Robot", robotId.toString());

        // Check existing
        List<DigitalPassport> existing = em.createQuery(
            "SELECT d FROM DigitalPassport d WHERE d.robot.id = :robotId", DigitalPassport.class)
            .setParameter("robotId", robotId).getResultList();

        DigitalPassport passport = existing.isEmpty() ? new DigitalPassport() : existing.get(0);
        passport.setRobot(robot);
        passport.setPassportData(passportData);
        passport.setIssuedAt(Instant.now());

        if (existing.isEmpty()) {
            em.persist(passport);
        } else {
            passport = em.merge(passport);
        }

        log.info("Issued digital passport for robot {}", robot.getSerialNumber());
        return passport;
    }

    @Transactional(readOnly = true)
    public DigitalPassport getPassport(Long robotId) {
        List<DigitalPassport> results = em.createQuery(
            "SELECT d FROM DigitalPassport d WHERE d.robot.id = :robotId", DigitalPassport.class)
            .setParameter("robotId", robotId).getResultList();
        if (results.isEmpty()) throw QooChainException.notFound("DigitalPassport", robotId.toString());
        return results.get(0);
    }

    @Transactional
    public Robot updateRobotStatus(Long robotId, String status) {
        Robot robot = em.find(Robot.class, robotId);
        if (robot == null) throw QooChainException.notFound("Robot", robotId.toString());
        robot.setStatus(Robot.RobotStatus.valueOf(status));
        if ("FINISHED".equals(status)) {
            robot.setManufacturedAt(LocalDate.now());
        }
        return em.merge(robot);
    }
}
