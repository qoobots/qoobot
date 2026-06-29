package com.qoobot.qoogear.developer.service;

import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.developer.domain.TestKit;
import com.qoobot.qoogear.developer.repository.TestKitRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class TestKitService {

    private final TestKitRepository kitRepo;

    public List<TestKit> listAvailable() {
        return kitRepo.findByIsAvailableTrue();
    }

    public List<TestKit> listByType(String kitType) {
        return kitRepo.findByKitType(kitType);
    }

    public TestKit getKit(Long id) {
        return kitRepo.findById(id)
                .orElseThrow(() -> QooGearException.notFound("TestKit", id));
    }

    @Transactional
    public TestKit createKit(TestKit kit) {
        return kitRepo.save(kit);
    }

    @Transactional
    public TestKit updateStock(Long id, int stock) {
        TestKit kit = getKit(id);
        kit.setStock(stock);
        kit.setIsAvailable(stock > 0);
        return kitRepo.save(kit);
    }
}
