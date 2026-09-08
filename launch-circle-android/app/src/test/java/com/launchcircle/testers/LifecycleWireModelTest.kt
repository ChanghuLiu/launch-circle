package com.launchcircle.testers

import com.google.gson.Gson
import com.launchcircle.testers.core.model.LaunchDashboard
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class LifecycleWireModelTest {
    private val gson = Gson()

    @Test
    fun waitingLifecycleDoesNotInventStartOrProgress() {
        val dashboard = gson.fromJson(
            """{
                "status":"WAITING_FOR_TESTERS","active_testers":11,
                "assigned_testers":11,"tester_target":15,"google_minimum":12,
                "testers_needed_for_minimum":1,"day":0,"total_days":14,
                "production_readiness":15,"today_tasks":0,"at_risk_testers":0,
                "feedback_count":0,"completed_missions":0,"estimated_ready_date":"",
                "approval_disclaimer":"No guarantee","testing_started_at":null,
                "testing_target_end_at":null,"qualifying_tester_count":11,
                "required_tester_count":12,"internally_production_ready":false,
                "internal_production_ready_reason":"Waiting for testers"
            }""",
            LaunchDashboard::class.java,
        )

        assertNull(dashboard.testing_started_at)
        assertEquals(0, dashboard.day)
        assertEquals(11, dashboard.qualifying_tester_count)
        assertFalse(dashboard.internally_production_ready)
    }

    @Test
    fun serverLifecycleFieldsMapTestingAndReadyStates() {
        val dashboard = gson.fromJson(
            """{
                "status":"TESTING","active_testers":12,"assigned_testers":12,
                "tester_target":15,"google_minimum":12,"testers_needed_for_minimum":0,
                "day":7,"total_days":14,"production_readiness":45,"today_tasks":2,
                "at_risk_testers":0,"feedback_count":0,"completed_missions":0,
                "estimated_ready_date":"2026-09-03","approval_disclaimer":"No guarantee",
                "testing_started_at":"2026-08-20T12:00:00Z",
                "testing_target_end_at":"2026-09-03T12:00:00Z",
                "qualifying_tester_count":12,"required_tester_count":12,
                "internally_production_ready":false,
                "internal_production_ready_reason":"Duration incomplete",
                "continuous_qualifying_testers":12,"replacement_testers":0,
                "elapsed_days":6,"days_remaining":7,"circle_health":"GOOD",
                "missions_completed":0,"missions_total_available":0,
                "coverage_shortage":0,"replacement_status":"NONE","risk_reason":""
            }""",
            LaunchDashboard::class.java,
        )

        assertEquals("2026-08-20T12:00:00Z", dashboard.testing_started_at)
        assertEquals(7, dashboard.day)
        assertEquals(12, dashboard.qualifying_tester_count)
        assertEquals(12, dashboard.required_tester_count)
        assertFalse(dashboard.internally_production_ready)

        val ready = dashboard.copy(
            status = "PRODUCTION_READY",
            day = 14,
            days_remaining = 0,
            internally_production_ready = true,
        )
        assertTrue(ready.internally_production_ready)
        assertEquals(14, ready.day)
    }
}
