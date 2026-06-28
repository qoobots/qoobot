package com.qoobot.qoocommunity.governance.controller;

import com.qoobot.qoocommunity.common.dto.ApiResponse;
import com.qoobot.qoocommunity.governance.domain.*;
import com.qoobot.qoocommunity.governance.service.GovernanceService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/governance")
@RequiredArgsConstructor
public class GovernanceController {

    private final GovernanceService governanceService;

    @GetMapping("/tsc")
    public ApiResponse<List<TscMember>> getTscMembers() {
        return ApiResponse.success(governanceService.getTscMembers());
    }

    @GetMapping("/sigs")
    public ApiResponse<List<Sig>> getSigs() {
        return ApiResponse.success(governanceService.getSigs());
    }

    @PostMapping("/sigs")
    public ApiResponse<Sig> createSig(@RequestBody Map<String, String> body) {
        return ApiResponse.success(governanceService.createSig(
                body.get("name"), body.get("slug"), body.get("description"), body.get("chairId")));
    }

    @GetMapping("/rfcs")
    public ApiResponse<List<Rfc>> listRfcs() {
        return ApiResponse.success(governanceService.listRfcs());
    }

    @GetMapping("/rfcs/{id}")
    public ApiResponse<Rfc> getRfc(@PathVariable Long id) {
        return ApiResponse.success(governanceService.getRfc(id));
    }

    @PostMapping("/rfcs")
    public ApiResponse<Rfc> createRfc(
            @RequestHeader("X-User-Id") String userId,
            @RequestBody Map<String, String> body) {
        return ApiResponse.success(governanceService.createRfc(userId,
                body.get("title"), body.get("content"), body.get("contentHtml")));
    }

    @PutMapping("/rfcs/{id}/submit")
    public ApiResponse<Rfc> submitForReview(@PathVariable Long id) {
        return ApiResponse.success(governanceService.submitForReview(id));
    }

    @PutMapping("/rfcs/{id}/start-voting")
    public ApiResponse<Rfc> startVoting(@PathVariable Long id) {
        return ApiResponse.success(governanceService.startVoting(id));
    }

    @PostMapping("/rfcs/{id}/vote")
    public ApiResponse<Rfc> castVote(
            @PathVariable Long id,
            @RequestBody Map<String, String> body) {
        return ApiResponse.success(governanceService.castVote(id, body.get("vote")));
    }

    @PutMapping("/rfcs/{id}/finalize")
    public ApiResponse<Rfc> finalizeRfc(
            @PathVariable Long id,
            @RequestBody Map<String, String> body) {
        return ApiResponse.success(governanceService.finalizeRfc(id, body.get("result")));
    }
}
