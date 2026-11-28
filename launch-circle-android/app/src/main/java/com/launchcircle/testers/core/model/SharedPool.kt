package com.launchcircle.testers.core.model

data class PoolOptIn(val enabled: Boolean)
data class PoolPreference(val enabled: Boolean, val active_apps: Int, val max_concurrent_apps: Int)
data class PoolOpportunity(val app_id: String, val name: String, val package_name: String, val workflow_steps: List<String>, val icon_url: String? = null, val owned: Boolean = false, val joined: Boolean = false, val available: Boolean = true, val no_test_required: Boolean = false)
data class PoolSupply(val app_id: String, val name: String, val listed: Boolean, val ready_to_list: Boolean, val accepted_participants: Int, val reported_joined_and_installed: Int, val missing_to_minimum: Int, val minimum: Int, val buffer_target: Int, val google_eligibility_confirmed: Boolean)

data class AppIntakeRequest(val name: String, val package_name: String, val developer_account_id: String, val workflow_steps: List<String>)
data class AppIntakeStatus(val id: String, val name: String, val package_name: String, val status: String, val app_id: String?)

data class AppTestGroup(
    val id: String,
    val name: String,
    val capacity: Int,
    val status: String,
    val my_group: Boolean,
    val joined: Boolean,
    val apps: List<PoolOpportunity>,
    val occupied_slots: Int = 0,
    val ready_to_join: Boolean = true,
    val test_required_app_count: Int = 0,
    val exempt_app_count: Int = 0,
    val member_count: Int = 0,
)
data class OwnerAppGroupOption(
    val id: String,
    val name: String,
    val status: String,
    val capacity: Int,
    val occupied_slots: Int,
    val remaining_app_slots: Int,
    val test_required_app_count: Int = 0,
    val exempt_app_count: Int = 0,
    val member_count: Int,
    val can_select: Boolean,
    val already_selected: Boolean,
    val owner_joined: Boolean = false,
)
data class OwnerAppProgress(
    val no_test_required: Boolean = false,
    val qualified_tester_count: Int = 0,
    val required_tester_count: Int = 12,
    val testing_started_at: String? = null,
    val day: Int = 0,
    val total_days: Int = 14,
    val status: String = "WAITING_FOR_TESTERS",
)
data class OwnerAppGroups(
    val app_id: String,
    val app_name: String,
    val groups: List<OwnerAppGroupOption>,
    val app_progress: OwnerAppProgress = OwnerAppProgress(),
)
data class AppGroupConsent(val consent: Boolean)
data class AppGroupJoinResult(
    val ok: Boolean,
    val group_id: String,
    val already_joined: Boolean,
    val new_app_tasks: Int = 0,
    val active_app_testers: Int = 0,
    val qualified_tester_count: Int = 0,
    val testing_started_at: String? = null,
    val day: Int = 0,
)
