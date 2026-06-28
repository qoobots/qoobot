package com.qoobot.qooauth.user.controller;

import com.qoobot.qooauth.common.dto.ApiResponse;
import com.qoobot.qooauth.user.service.UserService;
import com.qoobot.qooauth.user.service.UserService.UserProfile;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/v1/users")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    /**
     * Get current user profile.
     */
    @GetMapping("/me")
    public ResponseEntity<ApiResponse<UserProfile>> getCurrentUser(
            @RequestAttribute(value = "userId", required = false) String userId) {
        // In production, userId comes from JWT authentication filter
        String effectiveUserId = userId != null ? userId : "current_user";

        Optional<UserProfile> profile = userService.getUserProfile(effectiveUserId);
        return profile.map(p -> ResponseEntity.ok(ApiResponse.ok(p)))
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Update current user profile.
     */
    @PutMapping("/me")
    public ResponseEntity<ApiResponse<UserProfile>> updateProfile(
            @RequestAttribute(value = "userId", required = false) String userId,
            @RequestBody Map<String, String> body) {

        String effectiveUserId = userId != null ? userId : "current_user";
        UserProfile updated = userService.updateProfile(
                effectiveUserId,
                body.get("nickname"),
                body.get("language"),
                body.get("timezone"),
                body.get("avatar_hash")
        );
        return ResponseEntity.ok(ApiResponse.ok(updated));
    }

    /**
     * Verify email address.
     */
    @PostMapping("/me/verify-email")
    public ResponseEntity<ApiResponse<Void>> verifyEmail(
            @RequestAttribute(value = "userId", required = false) String userId,
            @RequestBody Map<String, String> body) {

        String effectiveUserId = userId != null ? userId : "current_user";
        userService.verifyEmail(effectiveUserId);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    /**
     * Request account deletion.
     */
    @DeleteMapping("/me")
    public ResponseEntity<ApiResponse<Void>> deleteAccount(
            @RequestAttribute(value = "userId", required = false) String userId) {

        String effectiveUserId = userId != null ? userId : "current_user";
        userService.requestAccountDeletion(effectiveUserId);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }
}
