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
