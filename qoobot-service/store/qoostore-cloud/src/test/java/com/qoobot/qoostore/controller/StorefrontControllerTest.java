package com.qoobot.qoostore.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.qoobot.qoostore.dto.response.ApiResponse;
import com.qoobot.qoostore.dto.response.SkillListResponse;
import com.qoobot.qoostore.dto.response.SkillResponse;
import com.qoobot.qoostore.entity.Category;
import com.qoobot.qoostore.service.StorefrontService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(StorefrontController.class)
class StorefrontControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private StorefrontService storefrontService;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void listSkills_shouldReturn200() throws Exception {
        SkillResponse skill = SkillResponse.builder()
                .id(1L)
                .skillId("com.test.cleaning")
                .name("智能清洁")
                .avgRating(4.5)
                .reviewCount(10L)
                .build();

        SkillListResponse listResponse = SkillListResponse.builder()
                .skills(List.of(skill))
                .page(0)
                .size(20)
                .totalElements(1)
                .totalPages(1)
                .build();

        when(storefrontService.listSkills(anyInt(), anyInt(), anyString()))
                .thenReturn(listResponse);

        mockMvc.perform(get("/api/v1/store/skills")
                        .param("page", "0")
                        .param("size", "20"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.skills[0].skillId").value("com.test.cleaning"));
    }

    @Test
    void getSkill_shouldReturn200() throws Exception {
        SkillResponse skill = SkillResponse.builder()
                .id(1L)
                .skillId("com.test.cleaning")
                .name("智能清洁")
                .avgRating(4.5)
                .reviewCount(10L)
                .build();

        when(storefrontService.getSkillDetail("com.test.cleaning")).thenReturn(skill);

        mockMvc.perform(get("/api/v1/store/skills/com.test.cleaning"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.skillId").value("com.test.cleaning"));
    }

    @Test
    void search_shouldReturn200() throws Exception {
        SkillListResponse listResponse = SkillListResponse.builder()
                .skills(List.of())
                .page(0)
                .size(20)
                .totalElements(0)
                .totalPages(0)
                .build();

        when(storefrontService.searchSkills(anyString(), anyInt(), anyInt()))
                .thenReturn(listResponse);

        mockMvc.perform(get("/api/v1/store/search")
                        .param("q", "清洁"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void listCategories_shouldReturn200() throws Exception {
        Category cat = Category.builder()
                .id(1L).name("家庭").slug("home").build();

        when(storefrontService.listCategories()).thenReturn(List.of(cat));

        mockMvc.perform(get("/api/v1/store/categories"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data[0].slug").value("home"));
    }

    @Test
    void getFeatured_shouldReturn200() throws Exception {
        SkillResponse skill = SkillResponse.builder()
                .id(1L)
                .skillId("com.test.featured")
                .name("精选技能")
                .build();

        when(storefrontService.getFeaturedSkills()).thenReturn(List.of(skill));

        mockMvc.perform(get("/api/v1/store/featured"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data[0].skillId").value("com.test.featured"));
    }

    @Test
    void getRankings_shouldReturn200() throws Exception {
        SkillListResponse listResponse = SkillListResponse.builder()
                .skills(List.of())
                .page(0)
                .size(20)
                .totalElements(0)
                .totalPages(0)
                .build();

        when(storefrontService.getRankings(anyString(), anyInt(), anyInt()))
                .thenReturn(listResponse);

        mockMvc.perform(get("/api/v1/store/rankings")
                        .param("type", "free"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }
}
