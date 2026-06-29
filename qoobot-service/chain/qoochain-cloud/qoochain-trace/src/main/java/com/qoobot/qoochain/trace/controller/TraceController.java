package com.qoobot.qoochain.trace.controller;

import com.qoobot.qoochain.trace.domain.*;
import com.qoobot.qoochain.trace.service.TraceService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/traceability")
@RequiredArgsConstructor
public class TraceController {

    private final TraceService traceService;

    @PostMapping("/robots")
    @ResponseStatus(HttpStatus.CREATED)
    public Robot createRobot(@RequestBody Robot robot) {
        return traceService.createRobot(robot);
    }

    @GetMapping("/robots")
    public List<Robot> listRobots() {
        return traceService.listRobots();
    }

    @GetMapping("/robots/{id}")
    public Robot getRobot(@PathVariable Long id) {
        return traceService.getRobot(id);
    }

    @GetMapping("/robots/sn/{serialNumber}")
    public Robot getBySerialNumber(@PathVariable String serialNumber) {
        return traceService.getBySerialNumber(serialNumber);
    }

    @PutMapping("/robots/{id}/status")
    public Robot updateStatus(@PathVariable Long id, @RequestBody Map<String, String> body) {
        return traceService.updateRobotStatus(id, body.get("status"));
    }

    @PostMapping("/robots/{robotId}/assembly")
    @ResponseStatus(HttpStatus.CREATED)
    public AssemblyRecord recordAssembly(@PathVariable Long robotId, @RequestBody Map<String, Object> body) {
        Long stationId = Long.valueOf(body.get("stationId").toString());
        String operatorId = (String) body.get("operatorId");
        return traceService.recordAssembly(robotId, stationId, operatorId);
    }

    @PutMapping("/assembly/{recordId}/complete")
    public AssemblyRecord completeAssembly(@PathVariable Long recordId) {
        return traceService.completeAssembly(recordId);
    }

    @GetMapping("/robots/{robotId}/assembly")
    public List<AssemblyRecord> getAssemblyRecords(@PathVariable Long robotId) {
        return traceService.getAssemblyRecords(robotId);
    }

    @PostMapping("/robots/{robotId}/components")
    @ResponseStatus(HttpStatus.CREATED)
    public ComponentTrace recordComponent(@PathVariable Long robotId, @RequestBody Map<String, Object> body) {
        Long materialId = Long.valueOf(body.get("materialId").toString());
        String lotNumber = (String) body.get("lotNumber");
        Long supplierId = body.containsKey("supplierId") ? Long.valueOf(body.get("supplierId").toString()) : null;
        return traceService.recordComponent(robotId, materialId, lotNumber, supplierId);
    }

    @GetMapping("/robots/{robotId}/components")
    public List<ComponentTrace> getComponentTraces(@PathVariable Long robotId) {
        return traceService.getComponentTraces(robotId);
    }

    @GetMapping("/components/lot/{lotNumber}")
    public List<ComponentTrace> findByLotNumber(@PathVariable String lotNumber) {
        return traceService.findByLotNumber(lotNumber);
    }

    @PostMapping("/robots/{robotId}/passport")
    @ResponseStatus(HttpStatus.CREATED)
    public DigitalPassport issuePassport(@PathVariable Long robotId, @RequestBody Map<String, Object> passportData) {
        return traceService.issuePassport(robotId, passportData);
    }

    @GetMapping("/robots/{robotId}/passport")
    public DigitalPassport getPassport(@PathVariable Long robotId) {
        return traceService.getPassport(robotId);
    }
}
