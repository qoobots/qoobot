package com.qoobot.qoocommunity.contributor.controller;

import com.qoobot.qoocommunity.common.dto.ApiResponse;
import com.qoobot.qoocommunity.contributor.domain.Contributor;
import com.qoobot.qoocommunity.contributor.service.ContributorService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/contributors")
@RequiredArgsConstructor
public class ContributorController {

    private final ContributorService contributorService;

    @GetMapping("/{userId}")
    public ApiResponse<Contributor> getContributor(@PathVariable String userId) {
        return ApiResponse.success(contributorService.getContributor(userId));
    }

    @GetMapping("/top")
    public ApiResponse<List<Contributor>> getTopContributors() {
        return ApiResponse.success(contributorService.getTopContributors());
    }

    @PostMapping("/cla")
    public ApiResponse<Contributor> signCla(
            @RequestHeader("X-User-Id") String userId,
            @RequestBody Map<String, String> body) {
        return ApiResponse.success(contributorService.signCla(userId, body.get("claType")));
    }

    @GetMapping("/stats")
    public ApiResponse<Map<String, Long>> getStats() {
        return ApiResponse.success(Map.of("totalContributors", contributorService.getContributorCount()));
    }
}
