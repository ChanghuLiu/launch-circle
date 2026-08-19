package com.launchcircle.testers

import com.launchcircle.testers.core.launch.InviteCodeValidator
import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchDashboard
import com.launchcircle.testers.feature.launch.PilotUiLogic
import com.launchcircle.testers.feature.onboarding.PilotOnboarding
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PilotFlowTest {
    @Test
    fun inviteCodeValidationNormalizesPilotCodes() {
        assertTrue(InviteCodeValidator.isValid(" lc-8h4k2 "))
        assertEquals("LC-8H4K2", InviteCodeValidator.normalize(" lc-8h4k2 "))
        assertFalse(InviteCodeValidator.isValid("LC-123"))
        assertFalse(InviteCodeValidator.isValid("not-a-code"))
    }

    @Test
    fun onboardingHasExactlyThreeClearSteps() {
        assertEquals(3, PilotOnboarding.pages.size)
        assertTrue(PilotOnboarding.pages.first().title.contains("12 testers"))
        assertTrue(PilotOnboarding.pages.last().title.contains("Get tested"))
    }

    @Test
    fun googleGroupConfirmationAndColdStartAreRepresented() {
        val app = LaunchApp(
            "id", "owner", "Pilot", "com.example.pilot", "https://example.com",
            null, "WAITING_FOR_TESTERS", 15, null, null,
        )
        assertFalse(PilotUiLogic.isGoogleGroupSetupComplete(app))
        assertTrue(
            PilotUiLogic.isGoogleGroupSetupComplete(
                app.copy(google_group_configured = true, google_group_confirmed_at = "now"),
            ),
        )
        val dashboard = LaunchDashboard(
            "WAITING_FOR_TESTERS", 5, 5, 15, 12, 7, 0, 14,
            27, 0, 0, 0, 0, "2026-09-02",
            "Readiness guidance only.",
        )
        assertEquals("Need 7 more to reach the minimum.", PilotUiLogic.coldStartMessage(dashboard))
        assertNull(PilotUiLogic.coldStartMessage(dashboard.copy(testers_needed_for_minimum = 0)))
    }
}
