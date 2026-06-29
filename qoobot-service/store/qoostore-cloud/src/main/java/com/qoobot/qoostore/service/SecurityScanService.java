package com.qoobot.qoostore.service;

import com.qoobot.qoostore.entity.Submission;
import com.qoobot.qoostore.repository.SubmissionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class SecurityScanService {

    private final SubmissionRepository submissionRepository;

    @Async
    public void scanSubmission(Submission submission) {
        String scanId = UUID.randomUUID().toString();
        submission.setAutoScanId(scanId);
        submission.setStatus("auto_reviewing");
        submissionRepository.save(submission);

        log.info("Auto scan started: submissionId={}, scanId={}", submission.getId(), scanId);

        try {
            Thread.sleep(2000); // simulate scan time
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        Map<String, Object> scanResult = Map.of(
                "passed", true,
                "malwareDetected", false,
                "permissionAbuse", false,
                "suspiciousAPIs", new String[]{},
                "score", 95
        );

        submission.setScanResult(toJson(scanResult));
        submission.setStatus("manual_reviewing");
        submissionRepository.save(submission);

        log.info("Auto scan completed: submissionId={}, passed=true", submission.getId());
    }

    private String toJson(Map<String, Object> map) {
        StringBuilder sb = new StringBuilder("{");
        map.forEach((k, v) -> {
            sb.append("\"").append(k).append("\":");
            if (v instanceof String) sb.append("\"").append(v).append("\"");
            else if (v instanceof Boolean || v instanceof Number) sb.append(v);
            else if (v instanceof String[]) {
                sb.append("[");
                String[] arr = (String[]) v;
                for (int i = 0; i < arr.length; i++) {
                    if (i > 0) sb.append(",");
                    sb.append("\"").append(arr[i]).append("\"");
                }
                sb.append("]");
            }
            sb.append(",");
        });
        if (sb.charAt(sb.length() - 1) == ',') sb.setLength(sb.length() - 1);
        sb.append("}");
        return sb.toString();
    }
}
