package com.qoobot.qoochain.aftermarket.controller;

import com.qoobot.qoochain.aftermarket.domain.*;
import com.qoobot.qoochain.aftermarket.service.AftermarketService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/aftermarket")
@RequiredArgsConstructor
public class AftermarketController {

    private final AftermarketService aftermarketService;

    @PostMapping("/repair-orders")
    @ResponseStatus(HttpStatus.CREATED)
    public RepairOrder createOrder(@RequestBody RepairOrder order) {
        return aftermarketService.createRepairOrder(order);
    }

    @GetMapping("/repair-orders")
    public List<RepairOrder> listOrders() {
        return aftermarketService.listOrders();
    }

    @GetMapping("/repair-orders/{id}")
    public RepairOrder getOrder(@PathVariable Long id) {
        return aftermarketService.getRepairOrder(id);
    }

    @GetMapping("/repair-orders/number/{orderNumber}")
    public RepairOrder getByOrderNumber(@PathVariable String orderNumber) {
        return aftermarketService.getByOrderNumber(orderNumber);
    }

    @GetMapping("/repair-orders/robot/{robotId}")
    public List<RepairOrder> getOrdersByRobot(@PathVariable Long robotId) {
        return aftermarketService.getOrdersByRobot(robotId);
    }

    @PutMapping("/repair-orders/{orderId}/status")
    public RepairOrder updateStatus(@PathVariable Long orderId, @RequestBody Map<String, String> body) {
        return aftermarketService.updateOrderStatus(orderId, body.get("status"),
            body.get("diagnosisResult"), body.get("repairAction"));
    }

    @GetMapping("/repair-orders/fault/{category}")
    public List<RepairOrder> getFaultAnalysis(@PathVariable String category) {
        return aftermarketService.getFaultAnalysis(category);
    }

    @GetMapping("/spare-parts")
    public List<SparePart> listSpareParts() {
        return aftermarketService.listSpareParts();
    }

    @GetMapping("/spare-parts/low-stock")
    public List<SparePart> getLowStockParts() {
        return aftermarketService.getLowStockParts();
    }

    @PostMapping("/spare-parts")
    @ResponseStatus(HttpStatus.CREATED)
    public SparePart createSparePart(@RequestBody SparePart sparePart) {
        return aftermarketService.createOrUpdateSparePart(sparePart);
    }
}
