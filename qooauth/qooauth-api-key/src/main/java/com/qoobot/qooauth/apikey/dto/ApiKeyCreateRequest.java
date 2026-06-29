package com.qoobot.qooauth.apikey.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiKeyCreateRequest {

    @NotBlank(message = "API key name is required")
    @Size(max = 128, message = "Name must be at most 128 characters")
    private String name;

    private List<String> permissions;

    private Instant expiresAt;
}
