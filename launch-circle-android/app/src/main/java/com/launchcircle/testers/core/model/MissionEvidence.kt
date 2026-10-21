package com.launchcircle.testers.core.model

data class AssignmentEvidenceStatus(val assignment_status: String)

data class MissionEvidenceContext(
    val mission_id: String,
    val assignment_id: String,
    val package_name: String,
    val expected_version_code: Int?,
    val assignment_status: String,
    val goal: String,
    val steps: List<String>,
)

data class MissionStepEvidence(
    val instruction: String,
    val expected: String,
    val actual: String,
    val result: String,
)

data class MissionRunRequest(
    val idempotency_key: String,
    val execution_source: String = "HUMAN_MANUAL",
    val result: String,
    val package_name: String,
    val version_code: Int,
    val expected_version_code: Int,
    val device_key: String = "",
    val device_model: String = "",
    val android_api: Int = 0,
    val steps: List<MissionStepEvidence>,
    val note: String = "",
    val retest_of_id: String? = null,
)

data class MissionRunRecord(
    val id: String,
    val mission_id: String,
    val result: String,
    val execution_source: String,
    val version_code: Int,
)

data class EnrollmentEvidenceRequest(
    val event: String,
    val note: String,
    val source: String = "SELF_REPORTED",
)

/** Partial execution is not a pass; the unexecuted steps need a blocking reason. */
fun missionEvidenceOutcome(results: List<String>): String? = when {
    results.isEmpty() -> null
    results.any { it !in setOf("PASS", "FAIL", "BLOCKED", "NOT_RUN") } -> null
    "FAIL" in results -> "FAIL"
    "BLOCKED" in results -> "BLOCKED"
    results.all { it == "PASS" } -> "PASS"
    results.all { it == "NOT_RUN" } -> "NOT_RUN"
    else -> null
}


data class CampaignEvidenceSummary(
    val app_id: String,
    val package_name: String,
    val candidate_version_code: Int?,
    val assigned_participants: Int,
    val reported_joined_participants: Int,
    val owner_confirmed_joined_participants: Int,
    val reported_continuous_14_days: Int,
    val manual_reported_participants: Int,
    val total_runs: Int,
    val current_build_device_coverage: Int,
    val current_build_results: Map<String, Int>,
    val execution_sources: Map<String, Int>,
    val issues: List<CampaignEvidenceIssue>,
)

data class CampaignEvidenceIssue(
    val run_id: String,
    val reported_version_code: Int,
    val fixed_version_code: Int?,
    val state: String,
    val last_retest_result: String?,
)

data class EvidenceBuildRequest(val target_version_code: Int, val description: String)
