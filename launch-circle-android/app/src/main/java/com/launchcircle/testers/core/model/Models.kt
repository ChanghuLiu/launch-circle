package com.launchcircle.testers.core.model

data class TokenPair(
    val access_token: String,
    val refresh_token: String,
    val token_type: String,
)

data class UserProfile(
    val id: String,
    val login_email: String,
    val display_name: String?,
    val tester_email: String?,
    val tester_email_sharing_consent: Boolean,
    val country: String?,
    val languages: List<String>,
    val profile_ready: Boolean,
)

data class GoogleAuthRequest(val id_token: String)
data class DevelopmentLoginRequest(val email: String, val password: String)
data class DevelopmentUser(
    val id: String,
    val email: String,
    val display_name: String?,
    val country: String?,
    val reliability_score: Int,
)
data class RefreshRequest(val refresh_token: String)
data class LogoutRequest(val refresh_token: String)
data class UserUpdateRequest(
    val display_name: String?,
    val country: String?,
    val languages: List<String>,
)
data class TesterEmailRequest(val tester_email: String, val sharing_consent: Boolean)
data class DeviceUpdateRequest(
    val installation_id: String,
    val manufacturer: String,
    val model: String,
    val android_api: Int,
    val capabilities: List<String>,
)
