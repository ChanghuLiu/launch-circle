package com.launchcircle.testers

import com.google.gson.Gson
import com.launchcircle.testers.core.model.LaunchDashboard
import com.launchcircle.testers.core.model.TesterAssignment
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RecoveryWireModelTest {
    private val gson = Gson()

    @Test
    fun dashboardMapsAtRiskAndReplacementCoverageFromServer() {
        val dashboard = gson.fromJson(
            """{
                "status":"AT_RISK","active_testers":11,"assigned_testers":12,
                "tester_target":15,"google_minimum":12,"testers_needed_for_minimum":1,
                "day":6,"total_days":14,"production_readiness":40,"today_tasks":2,
                "at_risk_testers":1,"feedback_count":0,"completed_missions":0,
                "estimated_ready_date":"2026-09-03","approval_disclaimer":"No guarantee",
                "qualifying_tester_count":11,"required_tester_count":12,
                "coverage_shortage":1,"replacement_status":"REPLACEMENT_ASSIGNED",
                "risk_reason":"1 qualifying tester(s) needed to restore coverage."
            }""",
            LaunchDashboard::class.java,
        )

        assertEquals("AT_RISK", dashboard.status)
        assertEquals(11, dashboard.qualifying_tester_count)
        assertEquals(1, dashboard.coverage_shortage)
        assertEquals("REPLACEMENT_ASSIGNED", dashboard.replacement_status)
        assertTrue(dashboard.risk_reason.contains("1 qualifying tester"))
    }

    @Test
    fun assignmentMapsServerParticipationStateWithoutLocalHealthCalculation() {
        val assignment = gson.fromJson(
            """{
                "id":"assignment-1","app_id":"app-1","tester_id":"tester-1",
                "tester_label":"Tester","status":"ACTIVE","assigned_at":"2026-08-20T12:00:00Z",
                "opted_in_at":"2026-08-20T12:00:00Z","installed_at":"2026-08-20T12:00:00Z",
                "completed_at":null,"completed_missions":1,"total_missions":2,
                "health_status":"CRITICAL","participation_state":"CRITICAL"
            }""",
            TesterAssignment::class.java,
        )

        assertEquals("CRITICAL", assignment.participation_state)
        assertEquals("CRITICAL", assignment.health_status)
    }
}
