package com.qoobot.qoochain.line.service;

import com.qoobot.qoochain.common.exception.QooChainException;
import com.qoobot.qoochain.line.domain.*;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ProductionLineService {

    @PersistenceContext
    private EntityManager em;

    @Transactional(readOnly = true)
    public ProductionLine getLine(Long id) {
        return em.find(ProductionLine.class, id);
    }

    @Transactional(readOnly = true)
    public List<ProductionLine> listAll() {
        return em.createQuery("SELECT p FROM ProductionLine p ORDER BY p.lineCode", ProductionLine.class)
            .getResultList();
    }

    @Transactional
    public ProductionLine createLine(ProductionLine line) {
        line.setStatus(ProductionLine.LineStatus.ACTIVE);
        em.persist(line);
        log.info("Created production line {} ({})", line.getLineCode(), line.getLineName());
        return line;
    }

    @Transactional
    public Station addStation(Long lineId, Station station) {
        ProductionLine line = em.find(ProductionLine.class, lineId);
        if (line == null) throw QooChainException.notFound("ProductionLine", lineId.toString());
        station.setLine(line);
        em.persist(station);
        return station;
    }

    @Transactional(readOnly = true)
    public List<Station> getStations(Long lineId) {
        return em.createQuery(
            "SELECT s FROM Station s WHERE s.line.id = :lineId ORDER BY s.sequence", Station.class)
            .setParameter("lineId", lineId).getResultList();
    }

    @Transactional
    public SopStep addSopStep(Long stationId, SopStep step) {
        Station station = em.find(Station.class, stationId);
        if (station == null) throw QooChainException.notFound("Station", stationId.toString());
        step.setStation(station);
        em.persist(step);
        return step;
    }

    @Transactional(readOnly = true)
    public List<SopStep> getSopSteps(Long stationId) {
        return em.createQuery(
            "SELECT s FROM SopStep s WHERE s.station.id = :stationId ORDER BY s.stepNumber", SopStep.class)
            .setParameter("stationId", stationId).getResultList();
    }

    @Transactional
    public DfmCheck createDfmCheck(Long productId, DfmCheck check) {
        check.setProductId(productId);
        em.persist(check);
        return check;
    }

    @Transactional(readOnly = true)
    public List<DfmCheck> getDfmChecks(Long productId) {
        return em.createQuery(
            "SELECT d FROM DfmCheck d WHERE d.productId = :productId", DfmCheck.class)
            .setParameter("productId", productId).getResultList();
    }

    @Transactional
    public DfmCheck resolveDfmCheck(Long checkId, String resolution, String assignee) {
        DfmCheck check = em.find(DfmCheck.class, checkId);
        if (check == null) throw QooChainException.notFound("DfmCheck", checkId.toString());
        check.setStatus(DfmCheck.CheckStatus.RESOLVED);
        check.setResolution(resolution);
        check.setAssignee(assignee);
        check.setResolvedAt(java.time.Instant.now());
        return em.merge(check);
    }

    @Transactional
    public void calculateTakt(Long lineId) {
        List<Station> stations = getStations(lineId);
        ProductionLine line = em.find(ProductionLine.class, lineId);
        if (line != null) {
            int maxCycleTime = stations.stream().mapToInt(Station::getCycleTimeMin).max().orElse(0);
            line.setTaktTimeMin(maxCycleTime);
            if (maxCycleTime > 0) {
                line.setDailyCapacity(480 / maxCycleTime); // 8h shift
            }
            em.merge(line);
        }
    }
}
