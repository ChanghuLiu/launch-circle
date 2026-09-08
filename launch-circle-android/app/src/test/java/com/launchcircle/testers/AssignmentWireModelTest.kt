package com.launchcircle.testers

import com.google.gson.Gson
import com.launchcircle.testers.core.model.TestAssignment
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AssignmentWireModelTest {
    private val gson = Gson()

    @Test
    fun assignmentResponseMapsRealFieldsAndCompletionState() {
        val assignment = gson.fromJson(
            """{
                "id":"assignment-1","circle_id":"circle-1","app_id":"app-1",
                "app_name":"Circle App","package_name":"com.example.app",
                "opt_in_url":"https://play.google.com/apps/testing/com.example.app",
                "test_type":"CORE_FEATURE","status":"COMPLETED",
                "assignment_day":"2026-08-20","assigned_at":"2026-08-20T12:00:00Z",
                "completed_at":"2026-08-20T12:05:00Z","estimated_minutes":5
            }""",
            TestAssignment::class.java,
        )

        assertEquals("assignment-1", assignment.id)
        assertEquals("circle-1", assignment.circle_id)
        assertEquals("Circle App", assignment.app_name)
        assertEquals("CORE_FEATURE", assignment.test_type)
        assertEquals("COMPLETED", assignment.status)
        assertEquals("2026-08-20T12:05:00Z", assignment.completed_at)
    }

    @Test
    fun emptyOneAndTwoAssignmentResponsesRemainTruthful() {
        val empty = emptyList<TestAssignment>()
        val one = listOf(sampleAssignment("assignment-1"))
        val two = listOf(sampleAssignment("assignment-1"), sampleAssignment("assignment-2"))

        assertEquals(0, empty.size)
        assertEquals(1, one.size)
        assertEquals(2, two.size)
        assertNull(one.single().completed_at)
        assertEquals("ASSIGNED", two.last().status)
    }

    private fun sampleAssignment(id: String) = TestAssignment(
        id = id,
        circle_id = "circle-1",
        app_id = "app-1",
        app_name = "Circle App",
        package_name = "com.example.app",
        opt_in_url = "https://example.com",
        test_type = "APP_CHECK",
        status = "ASSIGNED",
        assignment_day = "2026-08-20",
        assigned_at = "2026-08-20T12:00:00Z",
        completed_at = null,
    )
}
