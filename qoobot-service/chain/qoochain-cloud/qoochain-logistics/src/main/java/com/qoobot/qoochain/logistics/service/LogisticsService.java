package com.qoobot.qoochain.logistics.service;

import com.qoobot.qoochain.common.exception.QooChainException;
import com.qoobot.qoochain.common.util.SerialNumberGenerator;
import com.qoobot.qoochain.logistics.domain.*;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class LogisticsService {

    @PersistenceContext
    private EntityManager em;

    @Transactional
    public SerialNumberPool createPool(String prefix, long start, long end) {
        SerialNumberPool pool = new SerialNumberPool();
        pool.setPrefix(prefix);
        pool.setStartNumber(start);
        pool.setEndNumber(end);
        pool.setCurrentNumber(start);
        em.persist(pool);
        log.info("Created SN pool {}-[{}, {}]", prefix, start, end);
        return pool;
    }

    @Transactional
    public String allocateSerialNumber(Long poolId) {
        SerialNumberPool pool = em.find(SerialNumberPool.class, poolId);
        if (pool == null) throw QooChainException.notFound("SerialNumberPool", poolId.toString());
        if (pool.getStatus() != SerialNumberPool.PoolStatus.ACTIVE) {
            throw QooChainException.badRequest("SN pool is not active");
        }
        if (pool.getCurrentNumber() > pool.getEndNumber()) {
            pool.setStatus(SerialNumberPool.PoolStatus.EXHAUSTED);
            em.merge(pool);
            throw QooChainException.badRequest("SN pool exhausted");
        }

        long seq = pool.getCurrentNumber();
        pool.setCurrentNumber(seq + 1);
        if (pool.getCurrentNumber() > pool.getEndNumber()) {
            pool.setStatus(SerialNumberPool.PoolStatus.EXHAUSTED);
        }
        em.merge(pool);

        LocalDate today = LocalDate.now();
        String sn = String.format("%s-%04d-%02d%02d-%04d", pool.getPrefix(),
            today.getYear(), today.getMonthValue(), today.getDayOfMonth(), seq);
        return sn;
    }

    @Transactional(readOnly = true)
    public List<SerialNumberPool> listPools() {
        return em.createQuery("SELECT p FROM SerialNumberPool p ORDER BY p.prefix", SerialNumberPool.class)
            .getResultList();
    }

    @Transactional
    public LogisticsRecord createLogisticsRecord(LogisticsRecord record) {
        em.persist(record);
        return record;
    }

    @Transactional
    public LogisticsRecord updateLogisticsStatus(Long recordId, String status) {
        LogisticsRecord record = em.find(LogisticsRecord.class, recordId);
        if (record == null) throw QooChainException.notFound("LogisticsRecord", recordId.toString());
        record.setStatus(status);
        record.setStatusUpdatedAt(java.time.Instant.now());
        if ("DELIVERED".equals(status)) {
            record.setActualDelivery(LocalDate.now());
        }
        log.info("Logistics record {} status updated to {}", recordId, status);
        return em.merge(record);
    }

    @Transactional(readOnly = true)
    public LogisticsRecord getLogisticsRecord(Long robotId) {
        List<LogisticsRecord> records = em.createQuery(
            "SELECT l FROM LogisticsRecord l WHERE l.robotId = :robotId ORDER BY l.createdAt DESC",
            LogisticsRecord.class).setParameter("robotId", robotId).setMaxResults(1).getResultList();
        if (records.isEmpty()) throw QooChainException.notFound("LogisticsRecord for robot", robotId.toString());
        return records.get(0);
    }

    @Transactional(readOnly = true)
    public List<LogisticsRecord> listByStatus(String status) {
        return em.createQuery(
            "SELECT l FROM LogisticsRecord l WHERE l.status = :status ORDER BY l.createdAt DESC",
            LogisticsRecord.class).setParameter("status", status).getResultList();
    }
}
