package com.qoobot.qooauth.developer.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SkillSignRequest {

    @NotBlank(message = "Skill hash is required")
    private String skillHash;

    @NotBlank(message = "Signature is required")
    private String signature;
}
