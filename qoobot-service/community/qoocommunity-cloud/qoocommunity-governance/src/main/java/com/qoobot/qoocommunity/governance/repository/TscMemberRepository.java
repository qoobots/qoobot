package com.qoobot.qoocommunity.governance.repository;

import com.qoobot.qoocommunity.governance.domain.TscMember;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface TscMemberRepository extends JpaRepository<TscMember, Long> {
    List<TscMember> findByIsActiveTrue();
}
