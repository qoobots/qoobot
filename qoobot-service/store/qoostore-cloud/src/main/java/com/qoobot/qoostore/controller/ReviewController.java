package com.qoobot.qoostore.controller;

import com.qoobot.qoostore.dto.response.ApiResponse;
import com.qoobot.qoostore.entity.Submission;
import com.qoobot.qoostore.service.ReviewService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/review")
@RequiredArgsConstructor
@Tag(name = "技能审核", description = "技能审核流程管理")
public class ReviewController {

    private final ReviewService reviewService;

    @GetMapping("/submissions")
    @Operation(summary = "待审核列表")
    public ApiResponse<Page<Submission>> listSubmissions(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(reviewService.getPendingSubmissions(page, size));
    }

    @GetMapping("/submissions/{submissionId}")
    @Operation(summary = "审核详情")
    public ApiResponse<Submission> getSubmission(@PathVariable Long submissionId) {
        return ApiResponse.success(reviewService.getSubmissionDetail(submissionId));
    }

    @PostMapping("/submissions/{submissionId}/approve")
    @Operation(summary = "审核通过")
    public ApiResponse<Void> approveSubmission(
            @PathVariable Long submissionId,
            @RequestParam UUID reviewerId) {
        reviewService.approveSubmission(submissionId, reviewerId);
        return ApiResponse.success("Approved", null);
    }

    @PostMapping("/submissions/{submissionId}/reject")
    @Operation(summary = "审核驳回")
    public ApiResponse<Void> rejectSubmission(
            @PathVariable Long submissionId,
            @RequestParam UUID reviewerId,
            @RequestParam String reason) {
        reviewService.rejectSubmission(submissionId, reviewerId, reason);
        return ApiResponse.success("Rejected", null);
    }

    @GetMapping("/submissions/count")
    @Operation(summary = "待审核数量")
    public ApiResponse<Long> pendingCount() {
        return ApiResponse.success(reviewService.getPendingCount());
    }
}
