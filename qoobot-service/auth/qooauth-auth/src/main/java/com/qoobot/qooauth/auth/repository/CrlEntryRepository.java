package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.CrlEntry;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface CrlEntryRepository extends JpaRepository<CrlEntry, String> {

    Optional<CrlEntry> findBySerialNumber(String serialNumber);

    List<CrlEntry> findAllByOrderByCrlNumberDesc();

    List<CrlEntry> findByCrlNumberGreaterThan(Long crlNumber);

    long count();
}
