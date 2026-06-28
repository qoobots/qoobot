package com.qoobot.qoogear.developer.service;

import com.qoobot.qoogear.common.dto.PageResponse;
import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.developer.domain.*;
import com.qoobot.qoogear.developer.repository.*;
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
public class ReferenceDesignService {

    private final ReferenceDesignRepository designRepo;

    public PageResponse<ReferenceDesign> listDesigns(String category, String keyword, Pageable pageable) {
        Page<ReferenceDesign> page;
        if (keyword != null && !keyword.isBlank()) {
            page = designRepo.findByTitleContainingIgnoreCase(keyword, pageable);
        } else if (category != null) {
            page = designRepo.findByCategory(category, pageable);
        } else {
            page = designRepo.findAll(pageable);
        }
        return PageResponse.of(page.getContent(), page.getTotalElements(),
                page.getNumber(), page.getSize());
    }

    public ReferenceDesign getDesign(Long id) {
        return designRepo.findById(id)
                .orElseThrow(() -> QooGearException.notFound("ReferenceDesign", id));
    }

    @Transactional
    public ReferenceDesign createDesign(ReferenceDesign design) {
        design.setPublishedAt(ZonedDateTime.now());
        return designRepo.save(design);
    }

    @Transactional
    public void incrementDownloads(Long id) {
        ReferenceDesign design = getDesign(id);
        design.setDownloadCount((design.getDownloadCount() != null ? design.getDownloadCount() : 0) + 1);
        designRepo.save(design);
    }
}
