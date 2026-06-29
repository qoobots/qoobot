package com.qoobot.qoochain.aftermarket.service;

import com.qoobot.qoochain.aftermarket.domain.*;
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
public class AftermarketService {

    @PersistenceContext
    private EntityManager em;

    @Transactional
    public RepairOrder createRepairOrder(RepairOrder order) {
        String orderNumber = String.format("RMA-%04d-%06d",
            java.time.Year.now().getValue(), System.currentTimeMillis() % 1000000);
        order.setOrderNumber(orderNumber);
        em.persist(order);
        log.info("Created repair order {}", orderNumber);
        return order;
    }

    @Transactional(readOnly = true)
    public RepairOrder getRepairOrder(Long id) {
        RepairOrder order = em.find(RepairOrder.class, id);
        if (order == null) throw QooChainException.notFound("RepairOrder", id.toString());
        return order;
    }

    @Transactional(readOnly = true)
    public RepairOrder getByOrderNumber(String orderNumber) {
        List<RepairOrder> orders = em.createQuery(
            "SELECT r FROM RepairOrder r WHERE r.orderNumber = :num", RepairOrder.class)
            .setParameter("num", orderNumber).getResultList();
        if (orders.isEmpty()) throw QooChainException.notFound("RepairOrder", orderNumber);
        return orders.get(0);
    }

    @Transactional(readOnly = true)
    public List<RepairOrder> getOrdersByRobot(Long robotId) {
        return em.createQuery(
            "SELECT r FROM RepairOrder r WHERE r.robotId = :robotId ORDER BY r.createdAt DESC",
            RepairOrder.class).setParameter("robotId", robotId).getResultList();
    }

    @Transactional(readOnly = true)
    public List<RepairOrder> listOrders() {
        return em.createQuery(
            "SELECT r FROM RepairOrder r ORDER BY r.createdAt DESC", RepairOrder.class)
            .setMaxResults(100).getResultList();
    }

    @Transactional
    public RepairOrder updateOrderStatus(Long orderId, String status, String diagnosisResult, String repairAction) {
        RepairOrder order = em.find(RepairOrder.class, orderId);
        if (order == null) throw QooChainException.notFound("RepairOrder", orderId.toString());
        order.setStatus(RepairOrder.RepairStatus.valueOf(status));
        if (diagnosisResult != null) order.setDiagnosisResult(diagnosisResult);
        if (repairAction != null) order.setRepairAction(repairAction);
        if ("CLOSED".equals(status)) order.setClosedAt(Instant.now());
        log.info("Repair order {} status updated to {}", order.getOrderNumber(), status);
        return em.merge(order);
    }

    @Transactional
    public SparePart createOrUpdateSparePart(SparePart sparePart) {
        List<SparePart> existing = em.createQuery(
            "SELECT s FROM SparePart s WHERE s.materialId = :mid AND s.warehouseCode = :wc",
            SparePart.class)
            .setParameter("mid", sparePart.getMaterialId())
            .setParameter("wc", sparePart.getWarehouseCode())
            .getResultList();

        if (existing.isEmpty()) {
            em.persist(sparePart);
            return sparePart;
        } else {
            SparePart sp = existing.get(0);
            sp.setStockQuantity(sparePart.getStockQuantity());
            sp.setSafetyStock(sparePart.getSafetyStock());
            sp.setReorderPoint(sparePart.getReorderPoint());
            return em.merge(sp);
        }
    }

    @Transactional(readOnly = true)
    public List<SparePart> listSpareParts() {
        return em.createQuery("SELECT s FROM SparePart s ORDER BY s.warehouseCode, s.materialId", SparePart.class)
            .getResultList();
    }

    @Transactional(readOnly = true)
    public List<SparePart> getLowStockParts() {
        return em.createQuery(
            "SELECT s FROM SparePart s WHERE s.stockQuantity <= s.reorderPoint", SparePart.class)
            .getResultList();
    }

    @Transactional(readOnly = true)
    public List<RepairOrder> getFaultAnalysis(String faultCategory) {
        return em.createQuery(
            "SELECT r FROM RepairOrder r WHERE r.faultCategory = :cat ORDER BY r.createdAt DESC",
            RepairOrder.class).setParameter("cat", faultCategory).getResultList();
    }
}
