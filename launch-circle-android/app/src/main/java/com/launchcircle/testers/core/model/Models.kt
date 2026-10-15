package com.launchcircle.testers.core.model

import com.google.gson.annotations.SerializedName

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

// Request contract for POST /v1/auth/google; keep the wire name through R8.
data class InstallAttribution(
    val source: String,
    val medium: String?,
    val campaign: String?,
)

data class GoogleAuthRequest(
    @SerializedName("id_token") val id_token: String,
    val acquisition_source: String? = null,
    val acquisition_medium: String? = null,
    val acquisition_campaign: String? = null,
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
