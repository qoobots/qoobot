package com.qoobot.qoocommunity.governance.service;

import com.qoobot.qoocommunity.common.exception.QooCommunityException;
import com.qoobot.qoocommunity.governance.domain.*;
import com.qoobot.qoocommunity.governance.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class GovernanceService {

    private final TscMemberRepository tscMemberRepository;
    private final SigRepository sigRepository;
    private final RfcRepository rfcRepository;

    public List<TscMember> getTscMembers() {
        return tscMemberRepository.findByIsActiveTrue();
    }

    public List<Sig> getSigs() {
        return sigRepository.findAll();
    }

    public Sig createSig(String name, String slug, String description, String chairId) {
        Sig sig = new Sig();
        sig.setName(name);
        sig.setSlug(slug);
        sig.setDescription(description);
        sig.setChairId(chairId);
        return sigRepository.save(sig);
    }

    public List<Rfc> listRfcs() {
        return rfcRepository.findAllByOrderByCreatedAtDesc();
    }

    public Rfc getRfc(Long id) {
        return rfcRepository.findById(id)
                .orElseThrow(() -> QooCommunityException.notFound("RFC not found: " + id));
    }

    @Transactional
    public Rfc createRfc(String userId, String title, String content, String contentHtml) {
        long count = rfcRepository.count() + 1;
        Rfc rfc = new Rfc();
        rfc.setTitle(title);
        rfc.setNumber(String.format("RFC-%04d", count));
        rfc.setContent(content);
        rfc.setContentHtml(contentHtml);
        rfc.setAuthorId(userId);
        return rfcRepository.save(rfc);
    }

    @Transactional
    public Rfc submitForReview(Long rfcId) {
        Rfc rfc = getRfc(rfcId);
        rfc.setStatus("REVIEW");
        rfc.setUpdatedAt(LocalDateTime.now());
        return rfcRepository.save(rfc);
    }

    @Transactional
    public Rfc startVoting(Long rfcId) {
        Rfc rfc = getRfc(rfcId);
        rfc.setStatus("VOTING");
        rfc.setUpdatedAt(LocalDateTime.now());
        return rfcRepository.save(rfc);
    }

    @Transactional
    public Rfc castVote(Long rfcId, String vote) {
        Rfc rfc = getRfc(rfcId);
        if (!"VOTING".equals(rfc.getStatus())) {
            throw QooCommunityException.badRequest("RFC is not in voting phase");
        }
        switch (vote) {
            case "YES" -> rfc.setVoteYes(rfc.getVoteYes() + 1);
            case "NO" -> rfc.setVoteNo(rfc.getVoteNo() + 1);
            case "ABSTAIN" -> rfc.setVoteAbstain(rfc.getVoteAbstain() + 1);
        }
        rfc.setUpdatedAt(LocalDateTime.now());
        return rfcRepository.save(rfc);
    }

    @Transactional
    public Rfc finalizeRfc(Long rfcId, String result) {
        Rfc rfc = getRfc(rfcId);
        rfc.setStatus(result); // ACCEPTED or REJECTED
        rfc.setUpdatedAt(LocalDateTime.now());
        return rfcRepository.save(rfc);
    }
}
