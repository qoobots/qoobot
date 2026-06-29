package com.qoobot.qoogear.standard.service;

import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.standard.domain.*;
import com.qoobot.qoogear.standard.repository.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit tests for StandardSpecService — spec lifecycle, categories, compatibility, checklists.
 */
@ExtendWith(MockitoExtension.class)
class StandardSpecServiceTest {

    @Mock private StandardSpecRepository specRepo;
    @Mock private StandardCategoryRepository categoryRepo;
    @Mock private CompatibilityMatrixRepository compatRepo;
    @Mock private TestChecklistRepository checklistRepo;

    @InjectMocks
    private StandardSpecService service;

    private StandardSpec spec;
    private StandardCategory category;

    @BeforeEach
    void setUp() {
        category = new StandardCategory();
        category.setId(1L);
        category.setName("末端执行器");
        category.setSlug("end-effector");
        category.setSortOrder(0);

        spec = new StandardSpec();
        spec.setId(1L);
        spec.setCategoryId(1L);
        spec.setTitle("Gripper Interface v2.0");
        spec.setSpecNumber("MFQ-SPEC-000001");
        spec.setVersion("2.0.0");
        spec.setStatus("draft");
        spec.setSpecDocUrl("https://docs.qoogear.com/specs/end-effector/gripper-v2");
    }

    // === Category Tests ===

    @Test
    void shouldListAllCategories() {
        when(categoryRepo.findAll()).thenReturn(List.of(category));
        List<StandardCategory> result = service.listCategories();
        assertEquals(1, result.size());
        assertEquals("末端执行器", result.get(0).getName());
    }

    @Test
    void shouldGetRootCategories() {
        when(categoryRepo.findByParentIdIsNull()).thenReturn(List.of(category));
        List<StandardCategory> result = service.getRootCategories();
        assertEquals(1, result.size());
    }

    @Test
    void shouldGetSubCategories() {
        StandardCategory sub = new StandardCategory();
        sub.setId(2L);
        sub.setName("Electric Gripper");
        sub.setParentId(1L);
        when(categoryRepo.findByParentId(1L)).thenReturn(List.of(sub));
        List<StandardCategory> result = service.getSubCategories(1L);
        assertEquals(1, result.size());
        assertEquals(1L, result.get(0).getParentId());
    }

    @Test
    void shouldCreateCategory() {
        when(categoryRepo.save(any(StandardCategory.class))).thenReturn(category);
        StandardCategory result = service.createCategory(category);
        assertNotNull(result);
        assertEquals("end-effector", result.getSlug());
    }

    // === Spec CRUD Tests ===

    @Test
    void shouldCreateSpecWithDraftStatus() {
        when(specRepo.save(any(StandardSpec.class))).thenAnswer(inv -> {
            StandardSpec s = inv.getArgument(0);
            s.setId(1L);
            s.setSpecNumber("MFQ-SPEC-000001");
            return s;
        });
        StandardSpec result = service.createSpec(spec);
        assertNotNull(result);
        assertEquals("draft", result.getStatus());
        assertNotNull(result.getSpecNumber());
        assertTrue(result.getSpecNumber().startsWith("MFQ-SPEC-"));
    }

    @Test
    void shouldGetSpecById() {
        when(specRepo.findById(1L)).thenReturn(Optional.of(spec));
        StandardSpec result = service.getSpec(1L);
        assertNotNull(result);
        assertEquals("Gripper Interface v2.0", result.getTitle());
    }

    @Test
    void shouldThrowWhenSpecNotFound() {
        when(specRepo.findById(999L)).thenReturn(Optional.empty());
        assertThrows(QooGearException.class, () -> service.getSpec(999L));
    }

    @Test
    void shouldUpdateDraftSpec() {
        spec.setStatus("draft");
        when(specRepo.findById(1L)).thenReturn(Optional.of(spec));
        when(specRepo.save(any(StandardSpec.class))).thenReturn(spec);

        StandardSpec update = new StandardSpec();
        update.setTitle("Gripper Interface v3.0");
        update.setDescription("Updated mechanical and electrical specs");

        StandardSpec result = service.updateSpec(1L, update);
        assertEquals("Gripper Interface v3.0", result.getTitle());
        assertEquals("Updated mechanical and electrical specs", result.getDescription());
    }

    @Test
    void shouldRejectUpdateOnPublishedSpec() {
        spec.setStatus("published");
        when(specRepo.findById(1L)).thenReturn(Optional.of(spec));

        StandardSpec update = new StandardSpec();
        update.setTitle("Modified after publish");

        assertThrows(QooGearException.class, () -> service.updateSpec(1L, update));
    }

    @Test
    void shouldPublishDraftSpec() {
        spec.setStatus("draft");
        when(specRepo.findById(1L)).thenReturn(Optional.of(spec));
        when(specRepo.save(any(StandardSpec.class))).thenReturn(spec);

        StandardSpec result = service.publishSpec(1L);
        assertEquals("published", result.getStatus());
        assertNotNull(result.getPublishedAt());
    }

    @Test
    void shouldRejectPublishNonDraftSpec() {
        spec.setStatus("published");
        when(specRepo.findById(1L)).thenReturn(Optional.of(spec));
        assertThrows(QooGearException.class, () -> service.publishSpec(1L));
    }

    @Test
    void shouldDeprecateSpec() {
        spec.setStatus("published");
        when(specRepo.findById(1L)).thenReturn(Optional.of(spec));
        when(specRepo.save(any(StandardSpec.class))).thenReturn(spec);

        StandardSpec result = service.deprecateSpec(1L);
        assertEquals("deprecated", result.getStatus());
        assertNotNull(result.getDeprecatedAt());
    }

    @Test
    void shouldGetSpecVersions() {
        StandardSpec v1 = new StandardSpec();
        v1.setId(1L);
        v1.setSpecNumber("MFQ-SPEC-000001");
        v1.setVersion("2.0.0");
        StandardSpec v0 = new StandardSpec();
        v0.setId(2L);
        v0.setSpecNumber("MFQ-SPEC-000001");
        v0.setVersion("1.0.0");

        when(specRepo.findBySpecNumberOrderByVersionDesc("MFQ-SPEC-000001"))
                .thenReturn(List.of(v1, v0));

        List<StandardSpec> versions = service.getSpecVersions("MFQ-SPEC-000001");
        assertEquals(2, versions.size());
        assertEquals("2.0.0", versions.get(0).getVersion());
    }

    @Test
    void shouldSearchSpecsByKeyword() {
        Page<StandardSpec> page = new PageImpl<>(List.of(spec));
        when(specRepo.searchByTitle(eq("Gripper"), any(Pageable.class))).thenReturn(page);

        var result = service.searchSpecs("Gripper", Pageable.unpaged());
        assertEquals(1, result.getTotal());
        assertEquals("Gripper Interface v2.0", result.getData().get(0).getTitle());
    }

    // === Compatibility Matrix Tests ===

    @Test
    void shouldGetCompatibilityForSpec() {
        CompatibilityMatrix matrix = new CompatibilityMatrix();
        matrix.setId(1L);
        matrix.setSpecIdA(1L);
        matrix.setSpecVersionA("2.0.0");
        matrix.setSpecIdB(2L);
        matrix.setSpecVersionB("1.0.0");
        matrix.setCompatibility("compatible");

        when(compatRepo.findBySpecIdA(1L)).thenReturn(List.of(matrix));
        List<CompatibilityMatrix> result = service.getCompatibilityForSpec(1L);
        assertEquals(1, result.size());
        assertEquals("compatible", result.get(0).getCompatibility());
    }

    @Test
    void shouldAddCompatibility() {
        CompatibilityMatrix matrix = new CompatibilityMatrix();
        matrix.setSpecIdA(1L);
        matrix.setSpecIdB(2L);
        matrix.setCompatibility("conditional");
        matrix.setConditionDesc("Requires adapter");

        when(compatRepo.save(any(CompatibilityMatrix.class))).thenReturn(matrix);
        CompatibilityMatrix result = service.addCompatibility(matrix);
        assertNotNull(result);
        assertEquals("conditional", result.getCompatibility());
    }

    // === Test Checklist Tests ===

    @Test
    void shouldGetChecklistForStandard() {
        TestChecklist item = new TestChecklist();
        item.setId(1L);
        item.setStandardId(1L);
        item.setTestItem("Mechanical fit test");
        item.setTestMethod("Mount accessory and verify tolerance");
        item.setCriteria("Tolerance < 0.1mm");
        item.setRequired(true);

        when(checklistRepo.findByStandardId(1L)).thenReturn(List.of(item));
        List<TestChecklist> result = service.getChecklist(1L);
        assertEquals(1, result.size());
        assertEquals("Mechanical fit test", result.get(0).getTestItem());
        assertTrue(result.get(0).getRequired());
    }

    @Test
    void shouldAddChecklistItem() {
        TestChecklist item = new TestChecklist();
        item.setStandardId(1L);
        item.setTestItem("Electrical signal test");

        when(checklistRepo.save(any(TestChecklist.class))).thenReturn(item);
        TestChecklist result = service.addChecklistItem(item);
        assertNotNull(result);
        assertEquals("Electrical signal test", result.getTestItem());
    }

    @Test
    void shouldRemoveChecklistItem() {
        doNothing().when(checklistRepo).deleteById(10L);
        service.removeChecklistItem(10L);
        verify(checklistRepo).deleteById(10L);
    }
}
