package com.launchcircle.testers.core.model

import org.junit.Assert.assertTrue
import org.junit.Test

class EvidenceReportTest {
    @Test fun readableExportPreservesSourceScopeAndUnconfirmedEligibility() {
        val json = """{"generated_at":"2026-10-21T00:00:00Z","summary":{"package_name":"com.example.fixture","google_eligibility_confirmed":false,"manual_reported_participants":0},"runs":[{"execution_source":"CODEX_ASSISTED","details":{"steps":[{"actual":"Original observation"}],"note":"Synthetic fixture only"},"retest_of_id":"original-failure"}]}"""
        val report = evidenceReportText(json)
        assertTrue(report.contains("Google eligibility is NOT confirmed"))
        assertTrue(report.contains("CODEX_ASSISTED"))
        assertTrue(report.contains("Original observation"))
        assertTrue(report.contains("Synthetic fixture only"))
        assertTrue(report.contains("original-failure"))
        assertTrue(report.contains("\"google_eligibility_confirmed\": false"))
    }
}
