package com.qoobot.qoochain.bom.controller;

import com.qoobot.qoochain.bom.domain.*;
import com.qoobot.qoochain.bom.service.SupplierService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/suppliers")
@RequiredArgsConstructor
public class SupplierController {

    private final SupplierService supplierService;

    @GetMapping
    public List<Supplier> listAll() {
        return supplierService.listAll();
    }

    @GetMapping("/{id}")
    public Supplier getSupplier(@PathVariable Long id) {
        return supplierService.getSupplier(id);
    }

    @GetMapping("/code/{code}")
    public Supplier getByCode(@PathVariable String code) {
        return supplierService.getByCode(code);
    }

    @GetMapping("/category/{category}")
    public List<Supplier> listByCategory(@PathVariable String category) {
        return supplierService.listByCategory(category);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Supplier createSupplier(@RequestBody @Valid Supplier supplier) {
        return supplierService.createSupplier(supplier);
    }

    @PutMapping("/{id}")
    public Supplier updateSupplier(@PathVariable Long id, @RequestBody @Valid Supplier supplier) {
        return supplierService.updateSupplier(id, supplier);
    }

    @PutMapping("/{id}/rating")
    public Supplier updateRating(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        int rating = ((Number) body.get("rating")).intValue();
        String status = (String) body.get("status");
        return supplierService.updateRating(id, rating, status);
    }

    @GetMapping("/{id}/materials")
    public List<MaterialSupplier> getSupplierMaterials(@PathVariable Long id) {
        return supplierService.getSupplierMaterials(id);
    }
}
