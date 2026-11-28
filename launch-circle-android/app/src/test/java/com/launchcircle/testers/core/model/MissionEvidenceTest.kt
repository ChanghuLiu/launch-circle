package com.launchcircle.testers.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class MissionEvidenceTest {
    @Test fun incompleteAndBlockedExecutionNeverPasses() {
        assertNull(missionEvidenceOutcome(emptyList()))
        assertNull(missionEvidenceOutcome(listOf("PASS", "NOT_RUN")))
        assertNull(missionEvidenceOutcome(listOf("UNKNOWN")))
        assertEquals("BLOCKED", missionEvidenceOutcome(listOf("PASS", "BLOCKED")))
        assertEquals("FAIL", missionEvidenceOutcome(listOf("PASS", "FAIL", "NOT_RUN")))
        assertEquals("NOT_RUN", missionEvidenceOutcome(listOf("NOT_RUN", "NOT_RUN")))
        assertEquals("PASS", missionEvidenceOutcome(listOf("PASS", "PASS")))
    }
}
