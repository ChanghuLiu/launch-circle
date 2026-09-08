package com.launchcircle.testers.core.model

data class LaunchApp(
    val id: String,
    val owner_id: String,
    val name: String,
    val package_name: String,
    val opt_in_url: String,
    val google_group_url: String?,
    val status: String,
    val tester_target: Int,
    val testing_start_at: String?,
    val testing_end_at: String?,
    val google_group_mode: String = "LAUNCH_CIRCLE",
    val google_group_configured: Boolean = false,
    val google_group_confirmed_at: String? = null,
    val circle_id: String? = null,
)

data class CreateAppRequest(
    val name: String,
    val package_name: String,
    val opt_in_url: String,
    val google_group_url: String?,
    val google_group_mode: String = "LAUNCH_CIRCLE",
)

data class LaunchDashboard(
    val status: String,
    val active_testers: Int,
    val assigned_testers: Int,
    val tester_target: Int,
    val google_minimum: Int,
    val testers_needed_for_minimum: Int,
    val day: Int,
    val total_days: Int,
    val production_readiness: Int,
    val today_tasks: Int,
    val at_risk_testers: Int,
    val feedback_count: Int,
    val completed_missions: Int,
    val estimated_ready_date: String,
    val approval_disclaimer: String,
    val continuous_qualifying_testers: Int = 0,
    val replacement_testers: Int = 0,
    val elapsed_days: Int = 0,
    val days_remaining: Int = 14,
    val circle_health: String = "GOOD",
    val missions_completed: Int = 0,
    val missions_total_available: Int = 0,
    val testing_started_at: String? = null,
    val testing_target_end_at: String? = null,
    val lifecycle_complete: Boolean = false,
    val qualifying_tester_count: Int = active_testers,
    val required_tester_count: Int = 12,
    val internally_production_ready: Boolean = false,
    val internal_production_ready_reason: String = "",
    val coverage_shortage: Int = 0,
    val replacement_status: String = "NONE",
    val risk_reason: String = "",
)

data class TesterAssignment(
    val id: String,
    val app_id: String,
    val tester_id: String,
    val tester_label: String,
    val status: String,
    val assigned_at: String,
    val opted_in_at: String?,
    val installed_at: String?,
    val completed_at: String?,
    val completed_missions: Int,
    val total_missions: Int,
    val health_status: String = "NEW",
    val is_replacement: Boolean = false,
    val replacement_for_id: String? = null,
    val last_activity_at: String? = null,
    val testing_day: Int = 0,
    val participation_state: String = "ACTIVE",
)

data class TestMission(
    val id: String,
    val assignment_id: String,
    val app_id: String,
    val app_name: String,
    val opt_in_url: String,
    val mission_type: String,
    val scheduled_day: Int,
    val status: String,
    val due_at: String?,
    val completed_at: String?,
    val estimated_minutes: Int,
    val assignment_status: String = "ASSIGNED",
)

data class TestAssignment(
    val id: String,
    val circle_id: String,
    val app_id: String,
    val app_name: String,
    val package_name: String,
    val opt_in_url: String,
    val test_type: String,
    val status: String,
    val assignment_day: String,
    val assigned_at: String,
    val completed_at: String?,
    val estimated_minutes: Int = 5,
    val tester_user_id: String? = null,
)

data class AssignmentCoverage(
    val app_id: String,
    val assignment_count: Int,
    val completed_count: Int,
    val participating_members: Int,
)

data class FeedbackRequest(
    val launch_ok: Boolean?,
    val core_feature_ok: String?,
    val rating: Int?,
    val issue_text: String?,
    val suggestion_text: String?,
)

data class MissionFeedback(
    val id: String,
    val mission_id: String,
    val tester_label: String,
    val app_id: String,
    val mission_type: String,
    val launch_ok: Boolean?,
    val core_feature_ok: String?,
    val rating: Int?,
    val issue_text: String?,
    val suggestion_text: String?,
    val created_at: String,
)

data class InviteRequest(val invited_email: String? = null)

data class LaunchInvite(
    val id: String,
    val invite_code: String,
    val status: String,
    val share_url: String,
    val circle_id: String? = null,
    val invited_email: String? = null,
    val joined_user_id: String? = null,
    val created_at: String? = null,
    val expires_at: String? = null,
    val accepted_at: String? = null,
)

data class CircleMember(
    val id: String,
    val user_id: String,
    val display_name: String? = null,
    val member_label: String,
    val role: String,
    val status: String,
    val joined_at: String,
)

data class LaunchCircle(
    val id: String,
    val owner_id: String,
    val name: String,
    val max_members: Int = 15,
    val active_member_count: Int = 0,
    val members: List<CircleMember> = emptyList(),
)

data class MatchingResult(
    val assigned_now: Int,
    val assigned_total: Int,
    val active_testers: Int,
    val minimum_needed: Int,
    val target: Int,
    val remaining_to_target: Int,
)


data class GoogleGroupConfirmationRequest(val configured: Boolean = true)

data class PilotConfig(
    val product_name: String = "Launch Circle: 12 Testers",
    val google_group_email: String = "launch-circle-12-testers@googlegroups.com",
    val google_group_join_url: String = "https://groups.google.com/g/launch-circle-12-testers",
    val invite_base_url: String = "https://launchcircle.app/join",
)
