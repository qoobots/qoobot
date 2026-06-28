package com.qoobot.qoochain.logistics.controller;

import com.qoobot.qoochain.logistics.domain.*;
import com.qoobot.qoochain.logistics.service.LogisticsService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/logistics")
@RequiredArgsConstructor
public class LogisticsController {

    private final LogisticsService logisticsService;

    @PostMapping("/sn-pools")
    @ResponseStatus(HttpStatus.CREATED)
    public SerialNumberPool createPool(@RequestBody Map<String, Object> body) {
        String prefix = (String) body.get("prefix");
        long start = ((Number) body.get("startNumber")).longValue();
        long end = ((Number) body.get("endNumber")).longValue();
        return logisticsService.createPool(prefix, start, end);
    }

    @GetMapping("/sn-pools")
    public List<SerialNumberPool> listPools() {
        return logisticsService.listPools();
    }

    @PostMapping("/sn-pools/{poolId}/allocate")
    public Map<String, String> allocateSN(@PathVariable Long poolId) {
        String sn = logisticsService.allocateSerialNumber(poolId);
        return Map.of("serialNumber", sn);
    }

    @PostMapping("/records")
    @ResponseStatus(HttpStatus.CREATED)
    public LogisticsRecord createRecord(@RequestBody LogisticsRecord record) {
        return logisticsService.createLogisticsRecord(record);
    }

    @PutMapping("/records/{recordId}/status")
    public LogisticsRecord updateStatus(@PathVariable Long recordId, @RequestBody Map<String, String> body) {
        return logisticsService.updateLogisticsStatus(recordId, body.get("status"));
    }

    @GetMapping("/records/robot/{robotId}")
    public LogisticsRecord getByRobot(@PathVariable Long robotId) {
        return logisticsService.getLogisticsRecord(robotId);
    }

    @GetMapping("/records/status/{status}")
    public List<LogisticsRecord> listByStatus(@PathVariable String status) {
        return logisticsService.listByStatus(status);
    }
}
