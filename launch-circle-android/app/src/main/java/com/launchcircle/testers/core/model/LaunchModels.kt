package com.launchcircle.testers.core.model

import java.util.Locale

fun formatCheckoutAmount(cents: Int, currency: String = "USD"): String =
    "${currency.uppercase(Locale.US)} ${String.format(Locale.US, "%.2f", cents / 100.0)}"

fun managedCheckoutPriceLabel(listPrice: String?, actualPrice: String?, hasCredit: Boolean): String = when {
    actualPrice == null -> "Loading Google Play price…"
    hasCredit && listPrice != null -> "$listPrice list price · $actualPrice with your Managed credit"
    else -> actualPrice
}

fun parseCoreWorkflowSteps(value: String): List<String> =
    value.lineSequence().map { it.trim() }.filter { it.isNotEmpty() }.toList()

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
    val core_workflow_steps: List<String> = emptyList(),
    val google_group_mode: String = "LAUNCH_CIRCLE",
    val google_group_configured: Boolean = false,
    val google_group_confirmed_at: String? = null,
    val circle_id: String? = null,
    val play_developer_account_id: String? = null,
    val entitlement_status: String = "LEGACY",
)

data class CreateAppRequest(
    val name: String,
    val package_name: String,
    val opt_in_url: String,
    val google_group_url: String?,
    val google_group_mode: String = "LAUNCH_CIRCLE",
    val core_workflow_steps: List<String> = emptyList(),
    val play_developer_account_id: String = "",
    val circle_id: String? = null,
)

data class AdditionalAppCheckoutRequest(val play_developer_account_id: String)

data class AdditionalAppCheckout(
    val id: String,
    val status: String,
    val product_id: String,
    val amount_total: Int = 100,
    val currency: String = "USD",
    val app_id: String? = null,
)

data class GooglePlayPurchaseVerification(
    val purchase_id: String,
    val purchase_type: String,
    val purchase_token: String,
)

data class ManagedCheckout(
    val id: String,
    val status: String,
    val app_id: String,
    val product_id: String,
    val list_product_id: String = "managed_launch_15",
    val amount_total: Int = 1500,
    val currency: String = "USD",
    val list_price_total: Int = 1500,
    val credit_amount: Int = 0,
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
    val tester_minutes_reported: Int = 0,
    val developer_coordination_minutes: Int = 0,
    val coordination_entries: Int = 0,
    val remaining_reciprocal_missions: Int = 0,
    val remaining_reciprocal_minutes: Int = 0,
    val managed_offer_triggers: List<String>? = emptyList(),
    val managed_list_price_cents: Int = 1500,
    val managed_checkout_amount_cents: Int = 1500,
    val managed_credit_amount_cents: Int = 0,
    val managed_launch_purchased: Boolean = false,
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
    val goal: String = "",
    val steps: List<String> = emptyList(),
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
    val completion_result: String? = null,
    val time_spent_minutes: Int? = null,
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
    val completion_result: String? = null,
    val time_spent_minutes: Int? = null,
)

data class WorkloadSummary(
    val app_id: String,
    val completed_missions: Int = 0,
    val tester_minutes_reported: Int = 0,
    val tester_feedback_with_time: Int = 0,
    val tester_feedback_without_time: Int = 0,
    val estimated_unreported_tester_minutes: Int = 0,
    val developer_coordination_minutes: Int = 0,
    val coordination_entries: Int = 0,
)

data class ManagedOfferSummary(
    val app_id: String,
    val triggers: List<String> = emptyList(),
    val remaining_reciprocal_missions: Int = 0,
    val remaining_reciprocal_minutes: Int = 0,
    val managed_list_price_cents: Int = 1500,
    val managed_checkout_amount_cents: Int = 1500,
    val managed_credit_amount_cents: Int = 0,
    val managed_launch_purchased: Boolean = false,
)

data class CoordinationTimeRequest(val minutes: Int, val category: String = "COORDINATION")
data class ManagedOfferViewRequest(val trigger: String)

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
