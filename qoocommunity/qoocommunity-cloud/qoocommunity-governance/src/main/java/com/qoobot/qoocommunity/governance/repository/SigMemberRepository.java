package com.qoobot.qoocommunity.governance.repository;

import com.qoobot.qoocommunity.governance.domain.SigMember;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SigMemberRepository extends JpaRepository<SigMember, Long> {

    List<SigMember> findBySigId(Long sigId);

    List<SigMember> findByUserId(String userId);

    boolean existsBySigIdAndUserId(Long sigId, String userId);
}
