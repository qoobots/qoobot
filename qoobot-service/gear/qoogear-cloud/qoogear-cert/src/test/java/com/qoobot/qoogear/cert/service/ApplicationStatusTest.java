package com.qoobot.qoogear.cert.service;

import com.qoobot.qoogear.common.enums.ApplicationStatus;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for ApplicationStatus state machine transitions.
 */
class ApplicationStatusTest {

    @Test
    void shouldAllowDraftToSubmitted() {
        assertTrue(ApplicationStatus.DRAFT.canTransitionTo(ApplicationStatus.SUBMITTED));
    }

    @Test
    void shouldNotAllowDraftToApproved() {
        assertFalse(ApplicationStatus.DRAFT.canTransitionTo(ApplicationStatus.APPROVED));
    }

    @Test
    void shouldAllowSubmittedToComplianceCheck() {
        assertTrue(ApplicationStatus.SUBMITTED.canTransitionTo(ApplicationStatus.COMPLIANCE_CHECK));
    }

    @Test
    void shouldAllowSubmittedToRejected() {
        assertTrue(ApplicationStatus.SUBMITTED.canTransitionTo(ApplicationStatus.REJECTED));
    }

    @Test
    void shouldAllowComplianceCheckToReviewing() {
        assertTrue(ApplicationStatus.COMPLIANCE_CHECK.canTransitionTo(ApplicationStatus.REVIEWING));
    }

    @Test
    void shouldAllowReviewingToAssigned() {
        assertTrue(ApplicationStatus.REVIEWING.canTransitionTo(ApplicationStatus.ASSIGNED));
    }

    @Test
    void shouldAllowAssignedToTesting() {
        assertTrue(ApplicationStatus.ASSIGNED.canTransitionTo(ApplicationStatus.TESTING));
    }

    @Test
    void shouldAllowTestingToTestCompleted() {
        assertTrue(ApplicationStatus.TESTING.canTransitionTo(ApplicationStatus.TEST_COMPLETED));
    }

    @Test
    void shouldAllowTestCompletedToSecurityReview() {
        assertTrue(ApplicationStatus.TEST_COMPLETED.canTransitionTo(ApplicationStatus.SECURITY_REVIEW));
    }

    @Test
    void shouldAllowSecurityReviewToApproved() {
        assertTrue(ApplicationStatus.SECURITY_REVIEW.canTransitionTo(ApplicationStatus.APPROVED));
    }

    @Test
    void shouldAllowApprovedToRevoked() {
        assertTrue(ApplicationStatus.APPROVED.canTransitionTo(ApplicationStatus.REVOKED));
    }

    @Test
    void shouldAllowApprovedToExpired() {
        assertTrue(ApplicationStatus.APPROVED.canTransitionTo(ApplicationStatus.EXPIRED));
    }

    @Test
    void shouldNotAllowTerminalTransitions() {
        assertFalse(ApplicationStatus.REJECTED.canTransitionTo(ApplicationStatus.DRAFT));
        assertFalse(ApplicationStatus.REVOKED.canTransitionTo(ApplicationStatus.APPROVED));
        assertFalse(ApplicationStatus.EXPIRED.canTransitionTo(ApplicationStatus.APPROVED));
    }

    @Test
    void shouldCompleteFullHappyPath() {
        ApplicationStatus[] path = {
                ApplicationStatus.DRAFT,
                ApplicationStatus.SUBMITTED,
                ApplicationStatus.COMPLIANCE_CHECK,
                ApplicationStatus.REVIEWING,
                ApplicationStatus.ASSIGNED,
                ApplicationStatus.TESTING,
                ApplicationStatus.TEST_COMPLETED,
                ApplicationStatus.SECURITY_REVIEW,
                ApplicationStatus.APPROVED
        };
        for (int i = 0; i < path.length - 1; i++) {
            assertTrue(path[i].canTransitionTo(path[i + 1]),
                    String.format("Transition %s -> %s should be allowed", path[i], path[i + 1]));
        }
    }

    @Test
    void allStatusesHaveDisplayNames() {
        for (ApplicationStatus status : ApplicationStatus.values()) {
            assertNotNull(status.getDisplayName());
            assertFalse(status.getDisplayName().isBlank());
        }
    }
}
