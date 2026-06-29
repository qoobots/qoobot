package com.qoobot.qooauth.audit.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ComplianceReportRequest {

    @NotBlank
    private String reportType;          // SOC2 / ISO27001 / GDPR / CUSTOM

    @NotNull
    private Instant startTime;

    @NotNull
    private Instant endTime;

    private String format = "JSON";     // JSON / CSV / PDF
    private String actorFilter;         // Optional: filter by actor
    private String actionFilter;        // Optional: filter by action pattern
}
