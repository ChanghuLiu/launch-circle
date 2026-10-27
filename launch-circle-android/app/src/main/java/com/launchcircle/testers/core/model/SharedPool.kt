package com.launchcircle.testers.core.model

data class PoolOptIn(val enabled: Boolean)
data class PoolPreference(val enabled: Boolean, val active_apps: Int, val max_concurrent_apps: Int)
data class PoolOpportunity(val app_id: String, val name: String, val package_name: String, val workflow_steps: List<String>, val icon_url: String? = null, val owned: Boolean = false, val joined: Boolean = false, val available: Boolean = true)
data class PoolSupply(val app_id: String, val name: String, val listed: Boolean, val ready_to_list: Boolean, val accepted_participants: Int, val reported_joined_and_installed: Int, val missing_to_minimum: Int, val minimum: Int, val buffer_target: Int, val google_eligibility_confirmed: Boolean)

data class AppIntakeRequest(val name: String, val package_name: String, val developer_account_id: String, val workflow_steps: List<String>)
data class AppIntakeStatus(val id: String, val name: String, val package_name: String, val status: String, val app_id: String?)

data class AppTestGroup(val id: String, val name: String, val capacity: Int, val status: String, val my_group: Boolean, val joined: Boolean, val apps: List<PoolOpportunity>)
