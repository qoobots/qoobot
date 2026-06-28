package com.qoobot.qoochain.line.controller;

import com.qoobot.qoochain.line.domain.*;
import com.qoobot.qoochain.line.service.ProductionLineService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/production-lines")
@RequiredArgsConstructor
public class ProductionLineController {

    private final ProductionLineService lineService;

    @GetMapping
    public List<ProductionLine> listAll() { return lineService.listAll(); }

    @GetMapping("/{id}")
    public ProductionLine getLine(@PathVariable Long id) { return lineService.getLine(id); }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ProductionLine createLine(@RequestBody ProductionLine line) {
        return lineService.createLine(line);
    }

    @GetMapping("/{lineId}/stations")
    public List<Station> getStations(@PathVariable Long lineId) {
        return lineService.getStations(lineId);
    }

    @PostMapping("/{lineId}/stations")
    @ResponseStatus(HttpStatus.CREATED)
    public Station addStation(@PathVariable Long lineId, @RequestBody Station station) {
        return lineService.addStation(lineId, station);
    }

    @GetMapping("/stations/{stationId}/sop-steps")
    public List<SopStep> getSopSteps(@PathVariable Long stationId) {
        return lineService.getSopSteps(stationId);
    }

    @PostMapping("/stations/{stationId}/sop-steps")
    @ResponseStatus(HttpStatus.CREATED)
    public SopStep addSopStep(@PathVariable Long stationId, @RequestBody SopStep step) {
        return lineService.addSopStep(stationId, step);
    }

    @GetMapping("/{lineId}/dfm-checks")
    public List<DfmCheck> getDfmChecks(@PathVariable Long lineId) {
        return lineService.getDfmChecks(lineId);
    }

    @PostMapping("/products/{productId}/dfm-checks")
    @ResponseStatus(HttpStatus.CREATED)
    public DfmCheck createDfmCheck(@PathVariable Long productId, @RequestBody DfmCheck check) {
        return lineService.createDfmCheck(productId, check);
    }

    @PutMapping("/dfm-checks/{checkId}/resolve")
    public DfmCheck resolveDfmCheck(@PathVariable Long checkId, @RequestBody Map<String, String> body) {
        return lineService.resolveDfmCheck(checkId, body.get("resolution"), body.get("assignee"));
    }

    @PostMapping("/{lineId}/calculate-takt")
    public void calculateTakt(@PathVariable Long lineId) {
        lineService.calculateTakt(lineId);
    }
}
