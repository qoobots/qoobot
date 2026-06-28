package com.qoobot.qoochain.calibration.controller;

import com.qoobot.qoochain.calibration.domain.*;
import com.qoobot.qoochain.calibration.service.CalibrationService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/calibration")
@RequiredArgsConstructor
public class CalibrationController {

    private final CalibrationService calibService;

    @PostMapping("/sessions")
    @ResponseStatus(HttpStatus.CREATED)
    public CalibrationSession startSession(@RequestBody Map<String, Object> body) {
        Long robotId = Long.valueOf(body.get("robotId").toString());
        String calibType = (String) body.get("calibType");
        String operatorId = (String) body.get("operatorId");
        return calibService.startSession(robotId, calibType, operatorId);
    }

    @PostMapping("/sessions/{sessionId}/results")
    @ResponseStatus(HttpStatus.CREATED)
    public CalibrationResult recordResult(@PathVariable Long sessionId, @RequestBody CalibrationResult result) {
        return calibService.recordResult(sessionId, result);
    }

    @PutMapping("/sessions/{sessionId}/complete")
    public CalibrationSession completeSession(@PathVariable Long sessionId, @RequestBody Map<String, Boolean> body) {
        return calibService.completeSession(sessionId, body.getOrDefault("passed", true));
    }

    @GetMapping("/robots/{robotId}/sessions")
    public List<CalibrationSession> getSessions(@PathVariable Long robotId) {
        return calibService.getRobotSessions(robotId);
    }

    @GetMapping("/sessions/{sessionId}/results")
    public List<CalibrationResult> getResults(@PathVariable Long sessionId) {
        return calibService.getSessionResults(sessionId);
    }

    @GetMapping("/robots/{robotId}/latest")
    public CalibrationSession getLatestCalibration(@PathVariable Long robotId) {
        return calibService.getLatestCalibration(robotId);
    }
}
