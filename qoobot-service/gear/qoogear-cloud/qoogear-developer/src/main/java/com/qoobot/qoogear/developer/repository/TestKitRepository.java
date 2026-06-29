package com.qoobot.qoogear.developer.repository;

import com.qoobot.qoogear.developer.domain.TestKit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface TestKitRepository extends JpaRepository<TestKit, Long> {
    List<TestKit> findByKitType(String kitType);
    List<TestKit> findByIsAvailableTrue();
}
