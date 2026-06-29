package com.qoobot.qoochain.bom.service;

import com.qoobot.qoochain.bom.domain.*;
import com.qoobot.qoochain.bom.repository.*;
import com.qoobot.qoochain.common.exception.QooChainException;
import com.qoobot.qoochain.common.util.MaterialCodeGenerator;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class MaterialService {

    private final MaterialRepository materialRepository;
    private final MaterialSupplierRepository materialSupplierRepository;
    private final MaterialAlternativeRepository materialAlternativeRepository;
    private final CostRecordRepository costRecordRepository;

    @Transactional(readOnly = true)
    public Material getMaterial(Long id) {
        return materialRepository.findById(id)
            .orElseThrow(() -> QooChainException.notFound("Material", id.toString()));
    }

    @Transactional(readOnly = true)
    public Material getByCode(String materialCode) {
        return materialRepository.findByMaterialCode(materialCode)
            .orElseThrow(() -> QooChainException.notFound("Material", materialCode));
    }

    @Transactional(readOnly = true)
    public List<Material> listByCategory(String category) {
        return materialRepository.findByCategory(category);
    }

    @Transactional(readOnly = true)
    public List<Material> listAll() {
        return materialRepository.findAll();
    }

    @Transactional
    public Material createMaterial(Material material) {
        String code = MaterialCodeGenerator.generate(material.getCategory(), material.getManufacturerPn());
        material.setMaterialCode(code);
        log.info("Created material {} ({})", code, material.getMaterialName());
        return materialRepository.save(material);
    }

    @Transactional
    public Material updateMaterial(Long id, Material updated) {
        Material existing = getMaterial(id);
        existing.setMaterialName(updated.getMaterialName());
        existing.setCategory(updated.getCategory());
        existing.setSpecification(updated.getSpecification());
        existing.setManufacturer(updated.getManufacturer());
        existing.setManufacturerPn(updated.getManufacturerPn());
        existing.setLifecycle(updated.getLifecycle());
        existing.setLeadTimeDays(updated.getLeadTimeDays());
        existing.setMoq(updated.getMoq());
        existing.setRohsCompliant(updated.isRohsCompliant());
        existing.setReachCompliant(updated.isReachCompliant());
        return materialRepository.save(existing);
    }

    @Transactional
    public MaterialSupplier linkSupplier(Long materialId, Long supplierId, MaterialSupplier ms) {
        Material material = getMaterial(materialId);
        MaterialSupplier link = new MaterialSupplier();
        link.setMaterial(material);
        link.setSupplier(ms.getSupplier());
        link.setSupplierPn(ms.getSupplierPn());
        link.setUnitPrice(ms.getUnitPrice());
        link.setCurrency(ms.getCurrency());
        link.setPreferred(ms.isPreferred());
        return materialSupplierRepository.save(link);
    }

    @Transactional(readOnly = true)
    public List<MaterialSupplier> getMaterialSuppliers(Long materialId) {
        return materialSupplierRepository.findByMaterialId(materialId);
    }

    @Transactional
    public MaterialAlternative addAlternative(Long materialId, Long alternativeId, MaterialAlternative.Compatibility compatibility) {
        if (materialId.equals(alternativeId)) {
            throw QooChainException.badRequest("Material cannot be an alternative to itself");
        }
        MaterialAlternative alt = new MaterialAlternative();
        alt.setMaterial(getMaterial(materialId));
        alt.setAlternative(getMaterial(alternativeId));
        alt.setCompatibility(compatibility);
        return materialAlternativeRepository.save(alt);
    }

    @Transactional(readOnly = true)
    public List<MaterialAlternative> getAlternatives(Long materialId) {
        return materialAlternativeRepository.findByMaterialId(materialId);
    }

    @Transactional
    public CostRecord recordCost(Long materialId, Long supplierId, CostRecord record) {
        Material material = getMaterial(materialId);
        record.setMaterial(material);
        record.setSupplier(record.getSupplier());
        // Close previous active cost record for this material-supplier pair
        costRecordRepository.findByMaterialIdAndSupplierIdAndEffectiveToIsNull(materialId, supplierId)
            .ifPresent(prev -> {
                prev.setEffectiveTo(record.getEffectiveFrom().minusDays(1));
                costRecordRepository.save(prev);
            });
        return costRecordRepository.save(record);
    }

    @Transactional(readOnly = true)
    public List<CostRecord> getCostHistory(Long materialId) {
        return costRecordRepository.findByMaterialIdOrderByEffectiveFromDesc(materialId);
    }
}
