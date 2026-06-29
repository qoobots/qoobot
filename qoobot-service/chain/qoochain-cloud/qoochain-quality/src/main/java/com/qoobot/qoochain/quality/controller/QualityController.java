package com.qoobot.qoochain.quality.controller;

import com.qoobot.qoochain.quality.domain.*;
import com.qoobot.qoochain.quality.service.QualityService;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/quality")
@RequiredArgsConstructor
public class QualityController {

    private final QualityService qualityService;

    @PostMapping("/inspections")
    @ResponseStatus(HttpStatus.CREATED)
    public InspectionRecord createInspection(@RequestBody InspectionRecord record) {
        return qualityService.createInspection(record);
    }

    @PostMapping("/inspections/{inspectionId}/measurements")
    @ResponseStatus(HttpStatus.CREATED)
    public InspectionMeasurement addMeasurement(@PathVariable Long inspectionId,
                                                  @RequestBody InspectionMeasurement measurement) {
        return qualityService.addMeasurement(inspectionId, measurement);
    }

    @PutMapping("/inspections/{inspectionId}/finalize")
    public InspectionRecord finalizeInspection(@PathVariable Long inspectionId) {
        return qualityService.finalizeInspection(inspectionId);
    }

    @GetMapping("/inspections/robot/{robotId}")
    public List<InspectionRecord> getInspectionsByRobot(@PathVariable Long robotId) {
        return qualityService.getInspectionsByRobot(robotId);
    }

    @GetMapping("/inspections/type/{type}")
    public List<InspectionRecord> getInspectionsByType(@PathVariable String type) {
        return qualityService.getInspectionsByType(type);
    }

    @PostMapping("/burn-in")
    @ResponseStatus(HttpStatus.CREATED)
    public BurnInTest startBurnIn(@RequestBody Map<String, Object> body) {
        Long robotId = Long.valueOf(body.get("robotId").toString());
        int durationHours = ((Number) body.get("durationHours")).intValue();
        return qualityService.startBurnIn(robotId, durationHours);
    }

    @PutMapping("/burn-in/{testId}/complete")
    public BurnInTest completeBurnIn(@PathVariable Long testId, @RequestBody Map<String, Object> body) {
        boolean passed = (Boolean) body.getOrDefault("passed", true);
        String reason = (String) body.get("failureReason");
        return qualityService.completeBurnIn(testId, passed, reason);
    }

    @GetMapping("/burn-in/robot/{robotId}")
    public List<BurnInTest> getBurnInTests(@PathVariable Long robotId) {
        return qualityService.getBurnInTests(robotId);
    }

    @PostMapping("/spc/calculate")
    @ResponseStatus(HttpStatus.CREATED)
    public SpcStatistics calculateSpc(@RequestBody Map<String, Object> body) {
        String measurementName = (String) body.get("measurementName");
        String stationCode = (String) body.get("stationCode");
        Instant start = Instant.parse((String) body.get("periodStart"));
        Instant end = Instant.parse((String) body.get("periodEnd"));
        return qualityService.calculateSpc(measurementName, stationCode, start, end);
    }

    @GetMapping("/spc/{measurementName}")
    public List<SpcStatistics> getSpcHistory(@PathVariable String measurementName) {
        return qualityService.getSpcHistory(measurementName);
    }
}
