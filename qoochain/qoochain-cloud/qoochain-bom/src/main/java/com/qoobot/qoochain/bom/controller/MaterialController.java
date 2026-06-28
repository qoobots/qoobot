package com.qoobot.qoochain.bom.controller;

import com.qoobot.qoochain.bom.domain.*;
import com.qoobot.qoochain.bom.service.MaterialService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/materials")
@RequiredArgsConstructor
public class MaterialController {

    private final MaterialService materialService;

    @GetMapping
    public List<Material> listAll() {
        return materialService.listAll();
    }

    @GetMapping("/{id}")
    public Material getMaterial(@PathVariable Long id) {
        return materialService.getMaterial(id);
    }

    @GetMapping("/code/{code}")
    public Material getByCode(@PathVariable String code) {
        return materialService.getByCode(code);
    }

    @GetMapping("/category/{category}")
    public List<Material> listByCategory(@PathVariable String category) {
        return materialService.listByCategory(category);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Material createMaterial(@RequestBody @Valid Material material) {
        return materialService.createMaterial(material);
    }

    @PutMapping("/{id}")
    public Material updateMaterial(@PathVariable Long id, @RequestBody @Valid Material material) {
        return materialService.updateMaterial(id, material);
    }

    @PostMapping("/{materialId}/suppliers")
    @ResponseStatus(HttpStatus.CREATED)
    public MaterialSupplier linkSupplier(@PathVariable Long materialId,
                                          @RequestBody @Valid MaterialSupplierRequest request) {
        return materialService.linkSupplier(materialId, request.getSupplierId(), request.toLink());
    }

    @GetMapping("/{materialId}/suppliers")
    public List<MaterialSupplier> getSuppliers(@PathVariable Long materialId) {
        return materialService.getMaterialSuppliers(materialId);
    }

    @PostMapping("/{materialId}/alternatives")
    @ResponseStatus(HttpStatus.CREATED)
    public MaterialAlternative addAlternative(@PathVariable Long materialId,
                                               @RequestBody @Valid AlternativeRequest request) {
        return materialService.addAlternative(materialId, request.getAlternativeId(),
            MaterialAlternative.Compatibility.valueOf(request.getCompatibility()));
    }

    @GetMapping("/{materialId}/alternatives")
    public List<MaterialAlternative> getAlternatives(@PathVariable Long materialId) {
        return materialService.getAlternatives(materialId);
    }

    @GetMapping("/{materialId}/cost-history")
    public List<CostRecord> getCostHistory(@PathVariable Long materialId) {
        return materialService.getCostHistory(materialId);
    }

    @PostMapping("/{materialId}/cost-records")
    @ResponseStatus(HttpStatus.CREATED)
    public CostRecord recordCost(@PathVariable Long materialId, @RequestBody @Valid CostRecord record) {
        return materialService.recordCost(materialId, record.getSupplier().getId(), record);
    }

    @lombok.Data
    public static class MaterialSupplierRequest {
        private Long supplierId;
        private String supplierPn;
        private java.math.BigDecimal unitPrice;
        private String currency;
        private boolean isPreferred;

        MaterialSupplier toLink() {
            MaterialSupplier ms = new MaterialSupplier();
            ms.setSupplierPn(supplierPn);
            ms.setUnitPrice(unitPrice);
            ms.setCurrency(currency);
            ms.setPreferred(isPreferred);
            return ms;
        }
    }

    @lombok.Data
    public static class AlternativeRequest {
        private Long alternativeId;
        private String compatibility;
    }
}
