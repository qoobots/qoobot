package com.qoobot.qoochain.bom.service;

import com.qoobot.qoochain.bom.domain.*;
import com.qoobot.qoochain.bom.repository.*;
import com.qoobot.qoochain.common.exception.QooChainException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class BomService {

    private final BomRepository bomRepository;
    private final BomItemRepository bomItemRepository;
    private final ProductRepository productRepository;

    @Transactional(readOnly = true)
    public Bom getBom(Long bomId) {
        return bomRepository.findById(bomId)
            .orElseThrow(() -> QooChainException.notFound("BOM", bomId.toString()));
    }

    @Transactional(readOnly = true)
    public List<Bom> getBomsByProduct(Long productId) {
        return bomRepository.findByProductId(productId);
    }

    @Transactional
    public Bom createBom(Long productId, String version, Bom.BomType bomType, String createdBy) {
        Product product = productRepository.findById(productId)
            .orElseThrow(() -> QooChainException.notFound("Product", productId.toString()));

        if (bomRepository.findByProductIdAndVersionAndBomType(productId, version, bomType).isPresent()) {
            throw QooChainException.conflict(
                String.format("BOM version %s already exists for product %s", version, product.getModelCode()));
        }

        Bom bom = new Bom();
        bom.setProduct(product);
        bom.setVersion(version);
        bom.setBomType(bomType);
        bom.setCreatedBy(createdBy);
        bom.setStatus(Bom.BomStatus.DRAFT);
        bom.setEstimatedCost(BigDecimal.ZERO);
        return bomRepository.save(bom);
    }

    @Transactional
    public BomItem addBomItem(Long bomId, BomItem item) {
        Bom bom = getBom(bomId);
        if (bom.getStatus() == Bom.BomStatus.RELEASED || bom.getStatus() == Bom.BomStatus.FROZEN) {
            throw QooChainException.badRequest("Cannot modify a released or frozen BOM");
        }
        item.setBom(bom);
        BomItem saved = bomItemRepository.save(item);

        // Update total items count
        bom.setTotalItems(bomItemRepository.findByBomIdOrderBySortOrder(bomId).size());
        bomRepository.save(bom);

        return saved;
    }

    @Transactional(readOnly = true)
    public List<BomItem> getBomTree(Long bomId) {
        return bomItemRepository.findByBomIdAndParentItemIsNullOrderBySortOrder(bomId);
    }

    @Transactional(readOnly = true)
    public List<BomItem> getChildItems(Long bomId, Long parentItemId) {
        return bomItemRepository.findByBomIdAndParentItemId(bomId, parentItemId);
    }

    @Transactional
    public Bom releaseBom(Long bomId) {
        Bom bom = getBom(bomId);
        if (bom.getStatus() != Bom.BomStatus.DRAFT && bom.getStatus() != Bom.BomStatus.UNDER_REVIEW) {
            throw QooChainException.badRequest("Only DRAFT or UNDER_REVIEW BOM can be released");
        }
        // Calculate estimated cost
        BigDecimal totalCost = calculateBomCost(bomId);
        bom.setEstimatedCost(totalCost);
        bom.setStatus(Bom.BomStatus.RELEASED);
        bom.setReleasedAt(java.time.LocalDate.now());
        log.info("BOM {} released with estimated cost {}", bomId, totalCost);
        return bomRepository.save(bom);
    }

    @Transactional
    public void deleteBom(Long bomId) {
        Bom bom = getBom(bomId);
        if (bom.getStatus() == Bom.BomStatus.RELEASED || bom.getStatus() == Bom.BomStatus.FROZEN) {
            throw QooChainException.badRequest("Cannot delete a released or frozen BOM");
        }
        bomItemRepository.deleteByBomId(bomId);
        bomRepository.delete(bom);
        log.info("BOM {} deleted", bomId);
    }

    private BigDecimal calculateBomCost(Long bomId) {
        // Simplified: sum up all leaf items with material costs
        List<BomItem> allItems = bomItemRepository.findByBomIdOrderBySortOrder(bomId);
        return allItems.stream()
            .filter(item -> item.getMaterial() != null)
            .map(item -> BigDecimal.ZERO) // Placeholder; actual cost from supplier
            .reduce(BigDecimal.ZERO, BigDecimal::add);
    }
}
