package com.qoobot.qoostore.exception;

public class SkillNotFoundException extends RuntimeException {
    public SkillNotFoundException(String skillId) {
        super("Skill not found: " + skillId);
    }
}
