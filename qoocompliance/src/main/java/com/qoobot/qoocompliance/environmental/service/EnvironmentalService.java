package com.qoobot.qoocompliance.environmental.service;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;

/**
 * Environmental & Sustainability compliance service.
 *
 * Covers:
 * - RoHS (Restriction of Hazardous Substances)
 * - WEEE (Waste Electrical and Electronic Equipment)
 * - REACH (Registration, Evaluation, Authorisation of Chemicals)
 * - Carbon footprint reporting
 * - Energy efficiency labeling
 */
@Service
public class EnvironmentalService {

    // ===================================================================
    // RoHS Compliance
    // ===================================================================

    public EnvironmentalReport assessRoHS(String productId, RoHSRequest request) {
        EnvironmentalReport report = new EnvironmentalReport(
                UUID.randomUUID().toString(), productId, "RoHS",
                "有害物质限制 RoHS", "IN_PROGRESS", Instant.now()
        );

        List<EnvironmentalCheck> checks = new ArrayList<>();

        // EU RoHS (2011/65/EU + 2015/863)
        checks.add(new EnvironmentalCheck("ROHS-PB", "铅 (Pb)",
                "最大浓度值 < 0.1% (1000 ppm)",
                request.leadPpm() < 1000 ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("ROHS-HG", "汞 (Hg)",
                "最大浓度值 < 0.1% (1000 ppm)",
                request.mercuryPpm() < 1000 ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("ROHS-CD", "镉 (Cd)",
                "最大浓度值 < 0.01% (100 ppm)",
                request.cadmiumPpm() < 100 ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("ROHS-CR6", "六价铬 (Cr6+)",
                "最大浓度值 < 0.1% (1000 ppm)",
                request.cr6Ppm() < 1000 ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("ROHS-PBB", "多溴联苯 (PBB)",
                "最大浓度值 < 0.1% (1000 ppm)",
                request.pbbPpm() < 1000 ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("ROHS-PBDE", "多溴二苯醚 (PBDE)",
                "最大浓度值 < 0.1% (1000 ppm)",
                request.pbdePpm() < 1000 ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("ROHS-DEHP", "DEHP 邻苯二甲酸酯",
                "最大浓度值 < 0.1% (1000 ppm)",
                request.dehpPpm() < 1000 ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("ROHS-BBP", "BBP 邻苯二甲酸酯",
                "最大浓度值 < 0.1% (1000 ppm)",
                request.bbpPpm() < 1000 ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("ROHS-DBP", "DBP 邻苯二甲酸酯",
                "最大浓度值 < 0.1% (1000 ppm)",
                request.dbpPpm() < 1000 ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("ROHS-DIBP", "DIBP 邻苯二甲酸酯",
                "最大浓度值 < 0.1% (1000 ppm)",
                request.dibpPpm() < 1000 ? "PASS" : "FAIL", "P0"));

        // China RoHS (GB/T 26572)
        checks.add(new EnvironmentalCheck("ROHS-CN-001", "中国 RoHS 标识",
                "标明有害物质含量表 (SJ/T 11364)",
                request.hasChinaRohsLabel() ? "PASS" : "FAIL", "P0"));

        // Documentation
        checks.add(new EnvironmentalCheck("ROHS-DOC-001", "技术文档",
                "编制 RoHS 符合性技术文档",
                request.hasDoc() ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("ROHS-CE-001", "CE 标识引用",
                "CE 符合性声明中引用 RoHS 协调标准",
                request.hasCEDeclaration() ? "PASS" : "FAIL", "P0"));

        report.setChecks(checks);
        report.setOverallResult(computeOverall(checks));
        return report;
    }

    // ===================================================================
    // WEEE Compliance
    // ===================================================================

    public EnvironmentalReport assessWEEE(String productId, WEEERequest request) {
        EnvironmentalReport report = new EnvironmentalReport(
                UUID.randomUUID().toString(), productId, "WEEE",
                "电子废弃物回收 WEEE", "IN_PROGRESS", Instant.now()
        );

        List<EnvironmentalCheck> checks = new ArrayList<>();

        checks.add(new EnvironmentalCheck("WEEE-REG-001", "WEEE 注册",
                "在目的国 WEEE 注册机构注册",
                request.hasRegistration() ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("WEEE-LAB-001", "WEEE 标识",
                "产品上标识带叉轮式垃圾桶符号 (EN 50419)",
                request.hasLabel() ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("WEEE-DES-001", "可回收设计",
                "产品设计便于拆解和材料回收",
                request.hasRecyclableDesign() ? "PASS" : "FAIL", "P1"));
        checks.add(new EnvironmentalCheck("WEEE-INF-001", "回收信息",
                "向回收机构提供拆解和回收信息",
                request.hasRecyclingInfo() ? "PASS" : "FAIL", "P1"));
        checks.add(new EnvironmentalCheck("WEEE-COL-001", "回收目标",
                String.format("回收率 ≥ %.0f%%", request.recoveryRate() * 100),
                request.recoveryRate() >= 0.75 ? "PASS" : "FAIL", "P0"));
        checks.add(new EnvironmentalCheck("WEEE-REU-001", "再利用/再循环率",
                String.format("再利用+再循环率 ≥ %.0f%%", request.reuseRecycleRate() * 100),
                request.reuseRecycleRate() >= 0.65 ? "PASS" : "FAIL", "P0"));

        report.setChecks(checks);
        report.setOverallResult(computeOverall(checks));
        return report;
    }

    // ===================================================================
    // REACH Compliance
    // ===================================================================

    public EnvironmentalReport assessREACH(String productId, REACHRequest request) {
        EnvironmentalReport report = new EnvironmentalReport(
                UUID.randomUUID().toString(), productId, "REACH",
                "化学品注册评估授权限制 REACH", "IN_PROGRESS", Instant.now()
        );

        List<EnvironmentalCheck> checks = new ArrayList<>();

        // SVHC (Substances of Very High Concern)
        checks.add(new EnvironmentalCheck("REACH-SVHC-001", "SVHC 候选清单检查",
                String.format("含 %d 种 SVHC 物质", request.svhcCount()),
                request.svhcCount() == 0 ? "PASS" : "REVIEW", "P0"));

        // Article 33 duty to communicate
        if (request.svhcCount() > 0) {
            checks.add(new EnvironmentalCheck("REACH-ART33-001", "SVHC 信息传递 (Art.33)",
                    "SVHC > 0.1% 时向下游和消费者传递安全信息",
                    request.hasSvhcCommunication() ? "PASS" : "FAIL", "P0"));
        }

        // Authorization (Annex XIV)
        checks.add(new EnvironmentalCheck("REACH-AUT-001", "授权物质 (Annex XIV)",
                "是否使用需授权的物质",
                request.usesAnnexXIV() ? "REVIEW" : "PASS", "P0"));

        // Restriction (Annex XVII)
        checks.add(new EnvironmentalCheck("REACH-RES-001", "限制物质 (Annex XVII)",
                "产品是否满足 Annex XVII 限制条件",
                request.meetsAnnexXVII() ? "PASS" : "FAIL", "P0"));

        // SCIP database
        checks.add(new EnvironmentalCheck("REACH-SCIP-001", "SCIP 数据库申报",
                "SVHC > 0.1% 时向 ECHA SCIP 数据库申报",
                request.hasSCIPNotification() ? "PASS" : "FAIL", "P0"));

        // Registration
        checks.add(new EnvironmentalCheck("REACH-REG-001", "物质注册 (>1 t/a)",
                "年产量/进口量 > 1 吨的化学物质需注册",
                request.hasRegistration() ? "PASS" : "FAIL", "P1"));

        report.setChecks(checks);
        report.setOverallResult(computeOverall(checks));
        return report;
    }

    // ===================================================================
    // Carbon Footprint
    // ===================================================================

    public CarbonFootprintReport calculateCarbonFootprint(String productId, CarbonRequest request) {
        CarbonFootprintReport report = new CarbonFootprintReport(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        // Lifecycle phases
        List<CarbonPhase> phases = new ArrayList<>();

        // Raw materials
        double materialsCO2 = calculateMaterialsCO2(request);
        phases.add(new CarbonPhase("RAW_MATERIALS", "原材料获取",
                materialsCO2, request.materialsWeightKg() * 5.0));

        // Manufacturing
        double manufacturingCO2 = request.manufacturingEnergyKwh() * request.gridEmissionFactor();
        phases.add(new CarbonPhase("MANUFACTURING", "生产制造",
                manufacturingCO2, request.manufacturingEnergyKwh() * 0.5));

        // Distribution
        double distributionCO2 = request.transportDistanceKm() * request.transportEmissionFactor();
        phases.add(new CarbonPhase("DISTRIBUTION", "分销运输",
                distributionCO2, request.transportDistanceKm() * 0.08));

        // Use phase
        double useCO2 = request.lifetimeYears() * request.annualEnergyKwh() * request.gridEmissionFactor();
        phases.add(new CarbonPhase("USE_PHASE", "使用阶段",
                useCO2, request.lifetimeYears() * request.annualEnergyKwh() * 0.3));

        // End of life
        double eolCO2 = request.materialsWeightKg() * 0.5; // approximate
        phases.add(new CarbonPhase("END_OF_LIFE", "废弃回收",
                eolCO2, request.materialsWeightKg() * 0.2));

        double totalActual = phases.stream().mapToDouble(CarbonPhase::actualKgCO2e).sum();
        double totalBaseline = phases.stream().mapToDouble(CarbonPhase::baselineKgCO2e).sum();

        report.setPhases(phases);
        report.setTotalKgCO2e(totalActual);
        report.setBaselineKgCO2e(totalBaseline);
        report.setReductionPercent((1 - totalActual / totalBaseline) * 100);

        // Carbon neutrality
        report.setCarbonOffset(request.hasCarbonOffset() ? request.carbonOffsetKg() : 0);
        report.setNetKgCO2e(totalActual - report.getCarbonOffset());
        report.setCarbonNeutral(report.getNetKgCO2e() <= 0);

        return report;
    }

    // ===================================================================
    // Energy Efficiency
    // ===================================================================

    public EnergyEfficiencyReport assessEnergyEfficiency(String productId, EnergyRequest request) {
        EnergyEfficiencyReport report = new EnergyEfficiencyReport(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        List<EfficiencyCheck> checks = new ArrayList<>();

        // Standby power
        checks.add(new EfficiencyCheck("EEF-STB-001", "待机功耗",
                String.format("%.2f W (限值 ≤ 0.5 W)", request.standbyPowerW()),
                request.standbyPowerW() <= 0.5 ? "PASS" : "FAIL", "P0"));

        // Operating power
        checks.add(new EfficiencyCheck("EEF-OPR-001", "工作功耗",
                String.format("%.2f W (限值 ≤ %.0f W)", request.operatingPowerW(), request.powerLimitW()),
                request.operatingPowerW() <= request.powerLimitW() ? "PASS" : "FAIL", "P0"));

        // Energy label
        checks.add(new EfficiencyCheck("EEF-LAB-001", "能效标签",
                String.format("能效等级: %s", request.energyLabel()),
                request.hasEnergyLabel() ? "PASS" : "FAIL", "P0"));

        // Battery efficiency
        checks.add(new EfficiencyCheck("EEF-BAT-001", "电池充电效率",
                String.format("%.1f%% (目标 ≥ 85%%)", request.chargingEfficiency() * 100),
                request.chargingEfficiency() >= 0.85 ? "PASS" : "FAIL", "P1"));

        // Sleep mode
        checks.add(new EfficiencyCheck("EEF-SLP-001", "休眠模式功耗",
                String.format("%.2f W (限值 ≤ 0.3 W)", request.sleepPowerW()),
                request.sleepPowerW() <= 0.3 ? "PASS" : "FAIL", "P1"));

        // Energy Star (if applicable)
        checks.add(new EfficiencyCheck("EEF-EST-001", "ENERGY STAR 认证",
                request.hasEnergyStar() ? "已认证" : "未认证",
                request.hasEnergyStar() ? "PASS" : "PENDING", "P2"));

        // EU Energy Label
        checks.add(new EfficiencyCheck("EEF-EUL-001", "EU 能效标签 (2017/1369)",
                String.format("EPREL 注册号: %s", request.eprelId()),
                request.hasEPREL() ? "PASS" : "PENDING", "P0"));

        report.setChecks(checks);
        report.setOverallResult(checks.stream().noneMatch(c -> "FAIL".equals(c.result()) && "P0".equals(c.priority()))
                ? "COMPLIANT" : "NON_COMPLIANT");
        return report;
    }

    // ===================================================================
    // Environmental Dashboard
    // ===================================================================

    public EnvironmentalDashboard getDashboard(String productId) {
        EnvironmentalDashboard dashboard = new EnvironmentalDashboard();
        dashboard.setProductId(productId);

        dashboard.setComplianceAreas(List.of(
                new AreaStatus("RoHS", "有害物质限制", "NOT_STARTED", "EU/CN"),
                new AreaStatus("WEEE", "电子废弃物回收", "NOT_STARTED", "EU"),
                new AreaStatus("REACH", "化学品法规", "NOT_STARTED", "EU"),
                new AreaStatus("Carbon Footprint", "碳足迹", "NOT_STARTED", "Global"),
                new AreaStatus("Energy Efficiency", "能效", "NOT_STARTED", "Global"),
                new AreaStatus("Battery Directive", "电池指令", "NOT_STARTED", "EU"),
                new AreaStatus("Packaging", "包装废弃物", "NOT_STARTED", "EU")
        ));

        dashboard.setLastUpdated(Instant.now());
        return dashboard;
    }

    // ===================================================================
    // Helpers
    // ===================================================================

    private String computeOverall(List<EnvironmentalCheck> checks) {
        long failed = checks.stream().filter(c -> "FAIL".equals(c.result()) && "P0".equals(c.priority())).count();
        if (failed > 0) return "NON_COMPLIANT";
        long review = checks.stream().filter(c -> "REVIEW".equals(c.result())).count();
        if (review > 0) return "REVIEW_REQUIRED";
        return "COMPLIANT";
    }

    private double calculateMaterialsCO2(CarbonRequest request) {
        double steel = request.steelKg() * 1.85; // kgCO2e/kg steel
        double aluminum = request.aluminumKg() * 11.5; // kgCO2e/kg aluminum
        double plastic = request.plasticKg() * 3.1; // kgCO2e/kg plastic
        double electronics = request.electronicsKg() * 50.0; // kgCO2e/kg electronics (PCBs/chips)
        double battery = request.batteryKg() * 70.0; // kgCO2e/kg Li-ion battery
        return steel + aluminum + plastic + electronics + battery;
    }

    // ===================================================================
    // DTOs
    // ===================================================================

    public static class EnvironmentalReport {
        private String reportId;
        private String productId;
        private String regulation;
        private String regulationName;
        private String status;
        private Instant createdAt;
        private List<EnvironmentalCheck> checks = new ArrayList<>();
        private String overallResult;

        public EnvironmentalReport() {}
        public EnvironmentalReport(String reportId, String productId, String regulation,
                                   String regulationName, String status, Instant createdAt) {
            this.reportId = reportId;
            this.productId = productId;
            this.regulation = regulation;
            this.regulationName = regulationName;
            this.status = status;
            this.createdAt = createdAt;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public String getRegulation() { return regulation; }
        public void setRegulation(String r) { this.regulation = r; }
        public String getRegulationName() { return regulationName; }
        public void setRegulationName(String n) { this.regulationName = n; }
        public String getStatus() { return status; }
        public void setStatus(String s) { this.status = s; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public List<EnvironmentalCheck> getChecks() { return checks; }
        public void setChecks(List<EnvironmentalCheck> c) { this.checks = c; }
        public String getOverallResult() { return overallResult; }
        public void setOverallResult(String r) { this.overallResult = r; }
    }

    public record EnvironmentalCheck(String checkId, String title, String description,
                                      String result, String priority) {}

    public record RoHSRequest(double leadPpm, double mercuryPpm, double cadmiumPpm,
                               double cr6Ppm, double pbbPpm, double pbdePpm,
                               double dehpPpm, double bbpPpm, double dbpPpm,
                               double dibpPpm, boolean hasChinaRohsLabel,
                               boolean hasDoc, boolean hasCEDeclaration) {}

    public record WEEERequest(boolean hasRegistration, boolean hasLabel,
                               boolean hasRecyclableDesign, boolean hasRecyclingInfo,
                               double recoveryRate, double reuseRecycleRate) {}

    public record REACHRequest(int svhcCount, boolean hasSvhcCommunication,
                                boolean usesAnnexXIV, boolean meetsAnnexXVII,
                                boolean hasSCIPNotification, boolean hasRegistration) {}

    public static class CarbonFootprintReport {
        private String reportId;
        private String productId;
        private Instant calculatedAt;
        private List<CarbonPhase> phases = new ArrayList<>();
        private double totalKgCO2e;
        private double baselineKgCO2e;
        private double reductionPercent;
        private double carbonOffset;
        private double netKgCO2e;
        private boolean carbonNeutral;

        public CarbonFootprintReport() {}
        public CarbonFootprintReport(String reportId, String productId, Instant calculatedAt) {
            this.reportId = reportId;
            this.productId = productId;
            this.calculatedAt = calculatedAt;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public Instant getCalculatedAt() { return calculatedAt; }
        public void setCalculatedAt(Instant t) { this.calculatedAt = t; }
        public List<CarbonPhase> getPhases() { return phases; }
        public void setPhases(List<CarbonPhase> p) { this.phases = p; }
        public double getTotalKgCO2e() { return totalKgCO2e; }
        public void setTotalKgCO2e(double t) { this.totalKgCO2e = t; }
        public double getBaselineKgCO2e() { return baselineKgCO2e; }
        public void setBaselineKgCO2e(double b) { this.baselineKgCO2e = b; }
        public double getReductionPercent() { return reductionPercent; }
        public void setReductionPercent(double r) { this.reductionPercent = r; }
        public double getCarbonOffset() { return carbonOffset; }
        public void setCarbonOffset(double o) { this.carbonOffset = o; }
        public double getNetKgCO2e() { return netKgCO2e; }
        public void setNetKgCO2e(double n) { this.netKgCO2e = n; }
        public boolean isCarbonNeutral() { return carbonNeutral; }
        public void setCarbonNeutral(boolean c) { this.carbonNeutral = c; }
    }

    public record CarbonPhase(String phase, String phaseName, double actualKgCO2e,
                               double baselineKgCO2e) {}

    public record CarbonRequest(double materialsWeightKg, double steelKg, double aluminumKg,
                                 double plasticKg, double electronicsKg, double batteryKg,
                                 double manufacturingEnergyKwh, double gridEmissionFactor,
                                 double transportDistanceKm, double transportEmissionFactor,
                                 double lifetimeYears, double annualEnergyKwh,
                                 boolean hasCarbonOffset, double carbonOffsetKg) {}

    public static class EnergyEfficiencyReport {
        private String reportId;
        private String productId;
        private Instant assessedAt;
        private List<EfficiencyCheck> checks = new ArrayList<>();
        private String overallResult;

        public EnergyEfficiencyReport() {}
        public EnergyEfficiencyReport(String reportId, String productId, Instant assessedAt) {
            this.reportId = reportId;
            this.productId = productId;
            this.assessedAt = assessedAt;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public Instant getAssessedAt() { return assessedAt; }
        public void setAssessedAt(Instant t) { this.assessedAt = t; }
        public List<EfficiencyCheck> getChecks() { return checks; }
        public void setChecks(List<EfficiencyCheck> c) { this.checks = c; }
        public String getOverallResult() { return overallResult; }
        public void setOverallResult(String r) { this.overallResult = r; }
    }

    public record EfficiencyCheck(String checkId, String title, String description,
                                   String result, String priority) {}

    public record EnergyRequest(double standbyPowerW, double operatingPowerW,
                                 double powerLimitW, String energyLabel, boolean hasEnergyLabel,
                                 double chargingEfficiency, double sleepPowerW,
                                 boolean hasEnergyStar, String eprelId, boolean hasEPREL) {}

    public static class EnvironmentalDashboard {
        private String productId;
        private List<AreaStatus> complianceAreas = new ArrayList<>();
        private Instant lastUpdated;

        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public List<AreaStatus> getComplianceAreas() { return complianceAreas; }
        public void setComplianceAreas(List<AreaStatus> a) { this.complianceAreas = a; }
        public Instant getLastUpdated() { return lastUpdated; }
        public void setLastUpdated(Instant t) { this.lastUpdated = t; }
    }

    public record AreaStatus(String area, String description, String status, String markets) {}
}
