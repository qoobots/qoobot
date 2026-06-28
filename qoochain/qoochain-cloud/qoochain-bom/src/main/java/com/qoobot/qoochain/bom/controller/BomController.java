package com.qoobot.qoochain.bom.controller;

import com.qoobot.qoochain.bom.domain.*;
import com.qoobot.qoochain.bom.service.BomService;
import com.qoobot.qoochain.common.dto.PageResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/bom")
@RequiredArgsConstructor
public class BomController {

    private final BomService bomService;

    @GetMapping("/{bomId}")
    public Bom getBom(@PathVariable Long bomId) {
        return bomService.getBom(bomId);
    }

    @GetMapping("/product/{productId}")
    public List<Bom> listBoms(@PathVariable Long productId) {
        return bomService.getBomsByProduct(productId);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Bom createBom(@RequestBody @Valid CreateBomRequest request) {
        return bomService.createBom(request.getProductId(), request.getVersion(),
            Bom.BomType.valueOf(request.getBomType()), request.getCreatedBy());
    }

    @GetMapping("/{bomId}/tree")
    public List<BomItem> getBomTree(@PathVariable Long bomId) {
        return bomService.getBomTree(bomId);
    }

    @GetMapping("/{bomId}/children/{parentItemId}")
    public List<BomItem> getChildItems(@PathVariable Long bomId, @PathVariable Long parentItemId) {
        return bomService.getChildItems(bomId, parentItemId);
    }

    @PostMapping("/{bomId}/items")
    @ResponseStatus(HttpStatus.CREATED)
    public BomItem addBomItem(@PathVariable Long bomId, @RequestBody @Valid BomItem item) {
        return bomService.addBomItem(bomId, item);
    }

    @PostMapping("/{bomId}/release")
    public Bom releaseBom(@PathVariable Long bomId) {
        return bomService.releaseBom(bomId);
    }

    @DeleteMapping("/{bomId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteBom(@PathVariable Long bomId) {
        bomService.deleteBom(bomId);
    }

    // DTO
    @lombok.Data
    public static class CreateBomRequest {
        private Long productId;
        private String version;
        private String bomType;
        private String createdBy;
    }
}
