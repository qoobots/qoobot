package com.qoobot.qoochain.calibration.service;

import com.qoobot.qoochain.calibration.domain.*;
import com.qoobot.qoochain.common.exception.QooChainException;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class CalibrationService {

    @PersistenceContext
    private EntityManager em;

    @Transactional
    public CalibrationSession startSession(Long robotId, String calibType, String operatorId) {
        CalibrationSession session = new CalibrationSession();
        session.setRobotId(robotId);
        session.setCalibType(calibType);
        session.setOperatorId(operatorId);
        session.setSessionVersion(generateVersion(robotId));
        session.setStartedAt(Instant.now());
        em.persist(session);
        log.info("Started calibration session {} for robot {}", session.getSessionVersion(), robotId);
        return session;
    }

    @Transactional
    public CalibrationResult recordResult(Long sessionId, CalibrationResult result) {
        CalibrationSession session = em.find(CalibrationSession.class, sessionId);
        if (session == null) throw QooChainException.notFound("CalibrationSession", sessionId.toString());
        result.setSession(session);
        result.setPassed(isWithinSpec(result));
        em.persist(result);
        return result;
    }

    @Transactional
    public CalibrationSession completeSession(Long sessionId, boolean passed) {
        CalibrationSession session = em.find(CalibrationSession.class, sessionId);
        if (session == null) throw QooChainException.notFound("CalibrationSession", sessionId.toString());
        session.setStatus(passed ? CalibrationSession.SessionStatus.PASSED : CalibrationSession.SessionStatus.FAILED);
        session.setCompletedAt(Instant.now());
        log.info("Calibration session {} completed: {}", session.getSessionVersion(),
            passed ? "PASSED" : "FAILED");
        return em.merge(session);
    }

    @Transactional(readOnly = true)
    public List<CalibrationSession> getRobotSessions(Long robotId) {
        return em.createQuery(
            "SELECT s FROM CalibrationSession s WHERE s.robotId = :robotId ORDER BY s.startedAt DESC",
            CalibrationSession.class)
            .setParameter("robotId", robotId).getResultList();
    }

    @Transactional(readOnly = true)
    public List<CalibrationResult> getSessionResults(Long sessionId) {
        return em.createQuery(
            "SELECT r FROM CalibrationResult r WHERE r.session.id = :sessionId", CalibrationResult.class)
            .setParameter("sessionId", sessionId).getResultList();
    }

    @Transactional(readOnly = true)
    public CalibrationSession getLatestCalibration(Long robotId) {
        List<CalibrationSession> sessions = em.createQuery(
            "SELECT s FROM CalibrationSession s WHERE s.robotId = :robotId AND s.status = 'PASSED' ORDER BY s.completedAt DESC",
            CalibrationSession.class)
            .setParameter("robotId", robotId)
            .setMaxResults(1)
            .getResultList();
        return sessions.isEmpty() ? null : sessions.get(0);
    }

    private boolean isWithinSpec(CalibrationResult result) {
        if (result.getSpecLower() == null || result.getSpecUpper() == null) return true;
        if (result.getAccuracyValue() == null) return true;
        return result.getAccuracyValue().compareTo(result.getSpecLower()) >= 0
            && result.getAccuracyValue().compareTo(result.getSpecUpper()) <= 0;
    }

    private String generateVersion(Long robotId) {
        long count = em.createQuery(
            "SELECT COUNT(s) FROM CalibrationSession s WHERE s.robotId = :robotId", Long.class)
            .setParameter("robotId", robotId).getSingleResult();
        return String.format("cal-%04d", count + 1);
    }
}
