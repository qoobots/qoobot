package com.qoobot.qoocompliance.monitor.controller;

import com.qoobot.qoocompliance.monitor.service.RegulationMonitorService;
import com.qoobot.qoocompliance.monitor.service.RegulationMonitorService.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/regulations")
public class RegulationController {

    private final RegulationMonitorService monitorService;

    public RegulationController(RegulationMonitorService monitorService) {
        this.monitorService = monitorService;
    }

    /**
     * Get regulations for a market.
     */
    @GetMapping("/{market}")
    public ResponseEntity<List<Regulation>> getRegulations(@PathVariable String market) {
        return ResponseEntity.ok(monitorService.getRegulations(market));
    }

    /**
     * Get upcoming regulation changes.
     */
    @GetMapping("/{market}/upcoming")
    public ResponseEntity<List<Regulation>> getUpcomingChanges(@PathVariable String market) {
        return ResponseEntity.ok(monitorService.getUpcomingChanges(market));
    }

    /**
     * Get regulation change history.
     */
    @GetMapping("/{market}/changes")
    public ResponseEntity<List<RegulationChange>> getChangeHistory(@PathVariable String market) {
        return ResponseEntity.ok(monitorService.getChangeHistory(market));
    }
}
