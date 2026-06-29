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
public class SupplierService {

    private final SupplierRepository supplierRepository;
    private final MaterialSupplierRepository materialSupplierRepository;

    @Transactional(readOnly = true)
    public Supplier getSupplier(Long id) {
        return supplierRepository.findById(id)
            .orElseThrow(() -> QooChainException.notFound("Supplier", id.toString()));
    }

    @Transactional(readOnly = true)
    public Supplier getByCode(String supplierCode) {
        return supplierRepository.findBySupplierCode(supplierCode)
            .orElseThrow(() -> QooChainException.notFound("Supplier", supplierCode));
    }

    @Transactional(readOnly = true)
    public List<Supplier> listByCategory(String category) {
        return supplierRepository.findByCategory(category);
    }

    @Transactional(readOnly = true)
    public List<Supplier> listAll() {
        return supplierRepository.findAll();
    }

    @Transactional
    public Supplier createSupplier(Supplier supplier) {
        // Generate supplier code
        long count = supplierRepository.count();
        String code = MaterialCodeGenerator.generateSupplierCode(supplier.getCategory(), (int) count + 1);
        supplier.setSupplierCode(code);
        supplier.setStatus(Supplier.SupplierStatus.TRIAL);
        supplier.setRating(3);
        log.info("Created supplier {} ({})", code, supplier.getSupplierName());
        return supplierRepository.save(supplier);
    }

    @Transactional
    public Supplier updateSupplier(Long id, Supplier updated) {
        Supplier existing = getSupplier(id);
        existing.setSupplierName(updated.getSupplierName());
        existing.setCategory(updated.getCategory());
        existing.setCountry(updated.getCountry());
        existing.setContactName(updated.getContactName());
        existing.setContactEmail(updated.getContactEmail());
        existing.setContactPhone(updated.getContactPhone());
        return supplierRepository.save(existing);
    }

    @Transactional
    public Supplier updateRating(Long id, int rating, String status) {
        if (rating < 1 || rating > 5) {
            throw QooChainException.badRequest("Rating must be between 1 and 5");
        }
        Supplier supplier = getSupplier(id);
        supplier.setRating(rating);
        try {
            supplier.setStatus(Supplier.SupplierStatus.valueOf(status));
        } catch (IllegalArgumentException e) {
            throw QooChainException.badRequest("Invalid status: " + status);
        }
        log.info("Supplier {} rating updated to {} stars, status: {}", supplier.getSupplierCode(), rating, status);
        return supplierRepository.save(supplier);
    }

    @Transactional(readOnly = true)
    public List<MaterialSupplier> getSupplierMaterials(Long supplierId) {
        return materialSupplierRepository.findBySupplierId(supplierId);
    }
}
