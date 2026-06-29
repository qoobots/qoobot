package com.qoobot.qoogear.standard.service;

import com.qoobot.qoogear.common.dto.PageResponse;
import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.common.util.SpecNumberGenerator;
import com.qoobot.qoogear.standard.domain.*;
import com.qoobot.qoogear.standard.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.ZonedDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class StandardSpecService {

    private final StandardSpecRepository specRepo;
    private final StandardCategoryRepository categoryRepo;
    private final CompatibilityMatrixRepository compatRepo;
    private final TestChecklistRepository checklistRepo;

    // === Category Management ===

    public List<StandardCategory> listCategories() {
        return categoryRepo.findAll();
    }

    public List<StandardCategory> getRootCategories() {
        return categoryRepo.findByParentIdIsNull();
    }

    public List<StandardCategory> getSubCategories(Long parentId) {
        return categoryRepo.findByParentId(parentId);
    }

    @Transactional
    public StandardCategory createCategory(StandardCategory category) {
        return categoryRepo.save(category);
    }

    // === Spec Management ===

    public PageResponse<StandardSpec> listSpecs(Long categoryId, String status, Pageable pageable) {
        Page<StandardSpec> page;
        if (categoryId != null) {
            page = specRepo.findByCategoryId(categoryId, pageable);
        } else if (status != null) {
            page = specRepo.findByStatus(status, pageable);
        } else {
            page = specRepo.findAll(pageable);
        }
        return PageResponse.of(page.getContent(), page.getTotalElements(),
                page.getNumber(), page.getSize());
    }

    public StandardSpec getSpec(Long id) {
        return specRepo.findById(id)
                .orElseThrow(() -> QooGearException.notFound("StandardSpec", id));
    }

    public List<StandardSpec> getSpecVersions(String specNumber) {
        return specRepo.findBySpecNumberOrderByVersionDesc(specNumber);
    }

    @Transactional
    public StandardSpec createSpec(StandardSpec spec) {
        spec.setSpecNumber(SpecNumberGenerator.generate());
        spec.setStatus("draft");
        return specRepo.save(spec);
    }

    @Transactional
    public StandardSpec updateSpec(Long id, StandardSpec update) {
        StandardSpec spec = getSpec(id);
        if ("published".equals(spec.getStatus())) {
            throw QooGearException.badRequest("Cannot modify published spec; create new version instead");
        }
        if (update.getTitle() != null) spec.setTitle(update.getTitle());
        if (update.getDescription() != null) spec.setDescription(update.getDescription());
        if (update.getSpecDocUrl() != null) spec.setSpecDocUrl(update.getSpecDocUrl());
        if (update.getChangelog() != null) spec.setChangelog(update.getChangelog());
        return specRepo.save(spec);
    }

    @Transactional
    public StandardSpec publishSpec(Long id) {
        StandardSpec spec = getSpec(id);
        if (!"draft".equals(spec.getStatus())) {
            throw QooGearException.badRequest("Only draft specs can be published");
        }
        spec.setStatus("published");
        spec.setPublishedAt(ZonedDateTime.now());
        log.info("Standard spec published: {} v{}", spec.getSpecNumber(), spec.getVersion());
        return specRepo.save(spec);
    }

    @Transactional
    public StandardSpec deprecateSpec(Long id) {
        StandardSpec spec = getSpec(id);
        spec.setStatus("deprecated");
        spec.setDeprecatedAt(ZonedDateTime.now());
        return specRepo.save(spec);
    }

    public PageResponse<StandardSpec> searchSpecs(String keyword, Pageable pageable) {
        Page<StandardSpec> page = specRepo.searchByTitle(keyword, pageable);
        return PageResponse.of(page.getContent(), page.getTotalElements(),
                page.getNumber(), page.getSize());
    }

    // === Compatibility Matrix ===

    public List<CompatibilityMatrix> getCompatibilityForSpec(Long specId) {
        return compatRepo.findBySpecIdA(specId);
    }

    @Transactional
    public CompatibilityMatrix addCompatibility(CompatibilityMatrix matrix) {
        return compatRepo.save(matrix);
    }

    // === Test Checklist ===

    public List<TestChecklist> getChecklist(Long standardId) {
        return checklistRepo.findByStandardId(standardId);
    }

    @Transactional
    public TestChecklist addChecklistItem(TestChecklist item) {
        return checklistRepo.save(item);
    }

    @Transactional
    public void removeChecklistItem(Long id) {
        checklistRepo.deleteById(id);
    }
}
