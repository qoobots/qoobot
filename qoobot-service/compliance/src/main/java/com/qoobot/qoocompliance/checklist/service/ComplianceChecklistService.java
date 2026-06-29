package com.qoobot.qoocompliance.checklist.service;

import com.qoobot.qoocompliance.domain.ComplianceChecklist;
import com.qoobot.qoocompliance.domain.ComplianceItem;
import com.qoobot.qoocompliance.repository.ComplianceChecklistRepository;
import com.qoobot.qoocompliance.repository.ComplianceItemRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Compliance checklist engine.
 * Generates market-specific compliance checklists based on target regions,
 * tracks certification progress, and identifies gaps.
 *
 * Persistence layer: Spring Data JPA via ComplianceChecklistRepository and ComplianceItemRepository.
 */
@Service
public class ComplianceChecklistService {

    private final ComplianceChecklistRepository checklistRepo;
    private final ComplianceItemRepository itemRepo;

    // Predefined compliance checklists per market and category (reference templates, not persisted)
    private static final Map<String, List<ComplianceItem>> STANDARD_CHECKLISTS = Map.of(
        "CN", buildChinaChecklist(),
        "EU", buildEuChecklist(),
        "US", buildUsChecklist(),
        "JP", buildJapanChecklist()
    );

    public ComplianceChecklistService(ComplianceChecklistRepository checklistRepo,
                                       ComplianceItemRepository itemRepo) {
        this.checklistRepo = checklistRepo;
        this.itemRepo = itemRepo;
    }

    /**
     * Generate a compliance checklist for target markets.
     * Creates a ComplianceChecklist entity and copies template items as persisted entities.
     */
    @Transactional
    public ComplianceProject generateChecklist(String projectName, List<String> targetMarkets) {
        String checklistId = UUID.randomUUID().toString();

        ComplianceChecklist checklist = new ComplianceChecklist();
        checklist.setChecklistId(checklistId);
        checklist.setProjectId(checklistId); // projectId equals checklistId for simplicity
        checklist.setProjectName(projectName);
        checklist.setTargetMarkets(String.join(",", targetMarkets));
        checklist.setStatus("DRAFT");
        checklistRepo.save(checklist);

        List<ComplianceItem> items = new ArrayList<>();
        for (String market : targetMarkets) {
            List<ComplianceItem> marketItems = STANDARD_CHECKLISTS.getOrDefault(
                    market, Collections.emptyList());
            for (ComplianceItem dto : marketItems) {
                items.add(toEntity(dto, checklistId));
            }
        }
        itemRepo.saveAll(items);

        return toDto(checklist);
    }

    /**
     * Get all items for a project with optional category/status filtering.
     */
    public List<ComplianceItem> getItems(String projectId, String category, String status) {
        List<ComplianceItem> entities = itemRepo.findByChecklistId(projectId);

        return entities.stream()
                .filter(entity -> category == null || category.equals(entity.getCategory()))
                .filter(entity -> status == null || status.equals(entity.getStatus()))
                .map(this::toDto)
                .collect(Collectors.toList());
    }

    /**
     * Update item status, evidence, and notes.
     */
    @Transactional
    public ComplianceItem updateItemStatus(String projectId, String itemId, String status,
                                            String evidence, String notes) {
        ComplianceItem entity = itemRepo.findByItemId(itemId).orElse(null);
        if (entity == null) return null;

        entity.setStatus(status);
        entity.setEvidence(evidence);
        entity.setNotes(notes);
        // updatedAt is handled by @PreUpdate
        itemRepo.save(entity);

        return toDto(entity);
    }

    /**
     * Get project progress summary.
     */
    public ProjectProgress getProgress(String projectId) {
        List<ComplianceItem> entities = itemRepo.findByChecklistId(projectId);

        long total = entities.size();
        long compliant = entities.stream().filter(i -> "COMPLIANT".equals(i.getStatus())).count();
        long inProgress = entities.stream().filter(i -> "IN_PROGRESS".equals(i.getStatus())).count();
        long nonCompliant = entities.stream().filter(i -> "NON_COMPLIANT".equals(i.getStatus())).count();
        long notStarted = entities.stream().filter(i -> "NOT_STARTED".equals(i.getStatus())).count();

        double progress = total > 0 ? (double) compliant / total * 100 : 0;

        // Category breakdown
        Map<String, CategoryProgress> byCategory = new HashMap<>();
        for (ComplianceItem entity : entities) {
            CategoryProgress cp = byCategory.computeIfAbsent(entity.getCategory(),
                    k -> new CategoryProgress(k, 0, 0));
            cp.total++;
            if ("COMPLIANT".equals(entity.getStatus())) cp.compliant++;
        }

        return new ProjectProgress(projectId, total, compliant, inProgress,
                nonCompliant, notStarted, progress, byCategory);
    }

    /**
     * Identify compliance gaps — items that are blocking market entry.
     */
    public List<ComplianceItem> identifyGaps(String projectId, String targetMarket) {
        List<ComplianceItem> entities = itemRepo.findByChecklistId(projectId);

        return entities.stream()
                .filter(entity -> "ALL".equals(targetMarket) || targetMarket.equals(entity.getMarket()))
                .filter(entity -> !"COMPLIANT".equals(entity.getStatus()))
                .filter(entity -> "P0".equals(entity.getPriority()) || "P1".equals(entity.getPriority()))
                .map(this::toDto)
                .collect(Collectors.toList());
    }

    /**
     * Generate a compliance report for a project.
     */
    public ComplianceReport generateReport(String projectId) {
        ComplianceChecklist checklist = checklistRepo.findByChecklistId(projectId).orElse(null);
        if (checklist == null) return null;

        ComplianceProject project = toDto(checklist);
        ProjectProgress progress = getProgress(projectId);

        return new ComplianceReport(
                project,
                progress,
                identifyGaps(projectId, "ALL"),
                Instant.now()
        );
    }

    // --- Helper conversion methods ---

    private ComplianceItem toDto(ComplianceItem entity) {
        ComplianceItem dto = new ComplianceItem(
                entity.getItemId(),
                entity.getMarket(),
                entity.getCategory(),
                entity.getPriority(),
                entity.getTitle(),
                entity.getDescription(),
                entity.getStatus()
        );
        dto.setEvidence(entity.getEvidence());
        dto.setNotes(entity.getNotes());
        dto.setLastUpdated(toInstant(entity.getUpdatedAt()));
        return dto;
    }

    private ComplianceItem toEntity(ComplianceItem dto, String checklistId) {
        ComplianceItem entity = new ComplianceItem();
        entity.setItemId(dto.getItemId());
        entity.setChecklistId(checklistId);
        entity.setProjectId(checklistId);
        entity.setMarket(dto.getMarket());
        entity.setCategory(dto.getCategory());
        entity.setTitle(dto.getTitle());
        entity.setDescription(dto.getDescription());
        entity.setPriority(dto.getPriority());
        entity.setStatus(dto.getStatus());
        entity.setEvidence(dto.getEvidence());
        entity.setNotes(dto.getNotes());
        return entity;
    }

    private ComplianceProject toDto(ComplianceChecklist entity) {
        List<String> markets = entity.getTargetMarkets() != null && !entity.getTargetMarkets().isEmpty()
                ? Arrays.asList(entity.getTargetMarkets().split(","))
                : Collections.emptyList();
        return new ComplianceProject(
                entity.getChecklistId(),
                entity.getProjectName(),
                markets,
                entity.getStatus(),
                toInstant(entity.getCreatedAt())
        );
    }

    private static Instant toInstant(LocalDateTime ldt) {
        return ldt != null ? ldt.toInstant(ZoneOffset.UTC) : null;
    }

    // --- Checklist builders ---

    private static List<ComplianceItem> buildChinaChecklist() {
        List<ComplianceItem> items = new ArrayList<>();

        // Robot Safety
        items.add(new ComplianceItem("CN-SAF-001", "CN", "ROBOT_SAFETY", "P0",
                "GB 11291.1 工业机器人安全要求",
                "满足 GB 11291.1 安全等级要求", "NOT_STARTED"));
        items.add(new ComplianceItem("CN-SAF-002", "CN", "ROBOT_SAFETY", "P0",
                "GB/T 36008 协作机器人安全要求",
                "协作模式安全评估", "NOT_STARTED"));
        items.add(new ComplianceItem("CN-SAF-003", "CN", "ROBOT_SAFETY", "P1",
                "SIL 功能安全评估",
                "安全完整性等级 SIL 2 以上", "NOT_STARTED"));

        // Wireless
        items.add(new ComplianceItem("CN-WRL-001", "CN", "WIRELESS_EMC", "P0",
                "SRRC 无线电发射设备型号核准",
                "WiFi/BT/5G 模块 SRRC 认证", "NOT_STARTED"));
        items.add(new ComplianceItem("CN-WRL-002", "CN", "WIRELESS_EMC", "P0",
                "CCC 强制性产品认证",
                "整机 CCC 认证", "NOT_STARTED"));
        items.add(new ComplianceItem("CN-WRL-003", "CN", "WIRELESS_EMC", "P1",
                "EMC 电磁兼容测试 (GB/T 17626)",
                "辐射/传导骚扰、抗扰度测试通过", "NOT_STARTED"));

        // Privacy
        items.add(new ComplianceItem("CN-PRI-001", "CN", "PRIVACY_DATA", "P0",
                "PIPL 个人信息保护法合规",
                "个人信息处理规则、用户同意机制、数据跨境传输评估", "NOT_STARTED"));
        items.add(new ComplianceItem("CN-PRI-002", "CN", "PRIVACY_DATA", "P0",
                "数据安全法 (DSL) 合规",
                "数据分类分级、重要数据保护", "NOT_STARTED"));
        items.add(new ComplianceItem("CN-PRI-003", "CN", "PRIVACY_DATA", "P1",
                "个人信息安全规范 (GB/T 35273)",
                "隐私政策、数据最小化、安全措施", "NOT_STARTED"));

        // AI Ethics
        items.add(new ComplianceItem("CN-AIE-001", "CN", "AI_ETHICS", "P1",
                "生成式 AI 服务管理规定",
                "算法备案、内容安全评估", "NOT_STARTED"));
        items.add(new ComplianceItem("CN-AIE-002", "CN", "AI_ETHICS", "P2",
                "AI 伦理审查",
                "算法透明度、偏见检测报告", "NOT_STARTED"));

        // Environmental
        items.add(new ComplianceItem("CN-ENV-001", "CN", "ENVIRONMENTAL", "P1",
                "RoHS 有害物质限制",
                "六种有害物质检测报告", "NOT_STARTED"));

        return items;
    }

    private static List<ComplianceItem> buildEuChecklist() {
        List<ComplianceItem> items = new ArrayList<>();

        items.add(new ComplianceItem("EU-SAF-001", "EU", "ROBOT_SAFETY", "P0",
                "CE 机械指令 2006/42/EC",
                "机械安全合规、技术文件编制", "NOT_STARTED"));
        items.add(new ComplianceItem("EU-SAF-002", "EU", "ROBOT_SAFETY", "P0",
                "EN ISO 13482 个人护理机器人安全",
                "服务机器人安全标准符合性", "NOT_STARTED"));
        items.add(new ComplianceItem("EU-SAF-003", "EU", "ROBOT_SAFETY", "P0",
                "EN ISO 10218 工业机器人安全",
                "工业机器人安全要求", "NOT_STARTED"));

        items.add(new ComplianceItem("EU-WRL-001", "EU", "WIRELESS_EMC", "P0",
                "CE RED 无线电设备指令 2014/53/EU",
                "WiFi/BT 无线电测试", "NOT_STARTED"));
        items.add(new ComplianceItem("EU-WRL-002", "EU", "WIRELESS_EMC", "P0",
                "EMC 指令 2014/30/EU",
                "电磁兼容测试", "NOT_STARTED"));

        items.add(new ComplianceItem("EU-PRI-001", "EU", "PRIVACY_DATA", "P0",
                "GDPR 通用数据保护条例",
                "数据处理合法性基础、DPIA、数据保护官", "NOT_STARTED"));
        items.add(new ComplianceItem("EU-PRI-002", "EU", "PRIVACY_DATA", "P0",
                "ePrivacy 电子隐私指令",
                "Cookie 同意、电子通信隐私", "NOT_STARTED"));
        items.add(new ComplianceItem("EU-PRI-003", "EU", "PRIVACY_DATA", "P1",
                "数据跨境传输 (SCC/BCR)",
                "标准合同条款或约束性公司规则", "NOT_STARTED"));

        items.add(new ComplianceItem("EU-AIE-001", "EU", "AI_ETHICS", "P0",
                "EU AI Act 人工智能法案",
                "高风险 AI 系统分类、合规评估", "NOT_STARTED"));
        items.add(new ComplianceItem("EU-AIE-002", "EU", "AI_ETHICS", "P1",
                "算法透明度要求",
                "可解释性文档、人工监督机制", "NOT_STARTED"));

        items.add(new ComplianceItem("EU-ENV-001", "EU", "ENVIRONMENTAL", "P1",
                "RoHS 指令 2011/65/EU",
                "有害物质限制", "NOT_STARTED"));
        items.add(new ComplianceItem("EU-ENV-002", "EU", "ENVIRONMENTAL", "P1",
                "WEEE 指令 2012/19/EU",
                "电子废弃物回收", "NOT_STARTED"));
        items.add(new ComplianceItem("EU-ENV-003", "EU", "ENVIRONMENTAL", "P2",
                "REACH 法规",
                "化学品注册评估", "NOT_STARTED"));

        return items;
    }

    private static List<ComplianceItem> buildUsChecklist() {
        List<ComplianceItem> items = new ArrayList<>();

        items.add(new ComplianceItem("US-SAF-001", "US", "ROBOT_SAFETY", "P0",
                "UL 3300 服务/教育/商用机器人安全",
                "UL 安全认证", "NOT_STARTED"));
        items.add(new ComplianceItem("US-SAF-002", "US", "ROBOT_SAFETY", "P0",
                "ANSI/RIA R15.06 工业机器人安全",
                "工业机器人安全标准", "NOT_STARTED"));

        items.add(new ComplianceItem("US-WRL-001", "US", "WIRELESS_EMC", "P0",
                "FCC Part 15 无线电频率设备",
                "FCC 认证", "NOT_STARTED"));
        items.add(new ComplianceItem("US-WRL-002", "US", "WIRELESS_EMC", "P1",
                "FCC Part 18 ISM 设备",
                "工业科学医疗设备", "NOT_STARTED"));

        items.add(new ComplianceItem("US-PRI-001", "US", "PRIVACY_DATA", "P0",
                "CCPA/CPRA 加州消费者隐私法案",
                "消费者数据权利、Opt-out 机制", "NOT_STARTED"));
        items.add(new ComplianceItem("US-PRI-002", "US", "PRIVACY_DATA", "P1",
                "COPPA 儿童在线隐私保护",
                "13岁以下儿童数据保护", "NOT_STARTED"));

        items.add(new ComplianceItem("US-AIE-001", "US", "AI_ETHICS", "P1",
                "AI 治理框架 (NIST AI RMF)",
                "AI 风险管理框架符合性", "NOT_STARTED"));

        return items;
    }

    private static List<ComplianceItem> buildJapanChecklist() {
        List<ComplianceItem> items = new ArrayList<>();

        items.add(new ComplianceItem("JP-SAF-001", "JP", "ROBOT_SAFETY", "P0",
                "JIS B 8433 工业机器人安全",
                "日本工业机器人安全标准", "NOT_STARTED"));
        items.add(new ComplianceItem("JP-SAF-002", "JP", "ROBOT_SAFETY", "P1",
                "下一代机器人安全性认证 (METI)",
                "服务机器人安全指南", "NOT_STARTED"));

        items.add(new ComplianceItem("JP-WRL-001", "JP", "WIRELESS_EMC", "P0",
                "MIC 无线设备技术基准认证",
                "日本无线电认证 (技适)", "NOT_STARTED"));
        items.add(new ComplianceItem("JP-WRL-002", "JP", "WIRELESS_EMC", "P1",
                "VCCI EMC 电磁兼容",
                "自愿性 EMC 认证", "NOT_STARTED"));

        items.add(new ComplianceItem("JP-PRI-001", "JP", "PRIVACY_DATA", "P0",
                "APPI 个人信息保护法",
                "日本个人信息保护合规", "NOT_STARTED"));

        return items;
    }

    // --- DTOs ---

    public static class ComplianceItem {
        private String itemId;
        private String market;
        private String category;
        private String priority;
        private String title;
        private String description;
        private String status = "NOT_STARTED";
        private String evidence;
        private String notes;
        private Instant lastUpdated;

        public ComplianceItem(String itemId, String market, String category,
                              String priority, String title, String description, String status) {
            this.itemId = itemId;
            this.market = market;
            this.category = category;
            this.priority = priority;
            this.title = title;
            this.description = description;
            this.status = status;
            this.lastUpdated = Instant.now();
        }

        public String getItemId() { return itemId; }
        public void setItemId(String itemId) { this.itemId = itemId; }
        public String getMarket() { return market; }
        public void setMarket(String market) { this.market = market; }
        public String getCategory() { return category; }
        public void setCategory(String category) { this.category = category; }
        public String getPriority() { return priority; }
        public void setPriority(String priority) { this.priority = priority; }
        public String getTitle() { return title; }
        public void setTitle(String title) { this.title = title; }
        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public String getEvidence() { return evidence; }
        public void setEvidence(String evidence) { this.evidence = evidence; }
        public String getNotes() { return notes; }
        public void setNotes(String notes) { this.notes = notes; }
        public Instant getLastUpdated() { return lastUpdated; }
        public void setLastUpdated(Instant lastUpdated) { this.lastUpdated = lastUpdated; }
    }

    public record ComplianceProject(
            String projectId, String name, List<String> targetMarkets,
            String status, Instant createdAt
    ) {}

    public record ProjectProgress(
            String projectId, long total, long compliant, long inProgress,
            long nonCompliant, long notStarted, double progressPercent,
            Map<String, CategoryProgress> byCategory
    ) {}

    public record CategoryProgress(String category, int total, int compliant) {
        public double percent() { return total > 0 ? (double) compliant / total * 100 : 0; }
    }

    public record ComplianceReport(
            ComplianceProject project,
            ProjectProgress progress,
            List<ComplianceItem> criticalGaps,
            Instant generatedAt
    ) {}
}
