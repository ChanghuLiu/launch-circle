package com.launchcircle.testers.core.auth

import com.launchcircle.testers.core.model.DeviceUpdateRequest
import com.launchcircle.testers.core.model.DevelopmentLoginRequest
import com.launchcircle.testers.core.model.DevelopmentUser
import com.launchcircle.testers.core.model.GoogleAuthRequest
import com.launchcircle.testers.core.model.LogoutRequest
import com.launchcircle.testers.core.model.RefreshRequest
import com.launchcircle.testers.core.model.TesterEmailRequest
import com.launchcircle.testers.core.model.UserProfile
import com.launchcircle.testers.core.model.UserUpdateRequest
import com.launchcircle.testers.core.network.LaunchCircleApi
import com.launchcircle.testers.core.storage.TokenStore

class AuthRepository(
    private val api: LaunchCircleApi,
    private val tokenStore: TokenStore,
) {
    suspend fun exchangeGoogleToken(idToken: String): UserProfile {
        val tokens = api.googleAuth(GoogleAuthRequest(idToken))
        tokenStore.save(tokens.access_token, tokens.refresh_token, "google")
        return loadProfile()
    }

    suspend fun developmentLogin(email: String, password: String): UserProfile {
        val tokens = api.developmentLogin(DevelopmentLoginRequest(email, password))
        tokenStore.save(tokens.access_token, tokens.refresh_token, "development")
        return loadDevelopmentProfile()
    }

    suspend fun restoreSession(): UserProfile? {
        val refresh = tokenStore.refreshToken ?: return null
        return runCatching {
            val tokens = api.refresh(RefreshRequest(refresh))
            val mode = tokenStore.authMode ?: "google"
            tokenStore.save(tokens.access_token, tokens.refresh_token, mode)
            if (mode == "development") loadDevelopmentProfile() else loadProfile()
        }.getOrElse {
            tokenStore.clear()
            null
        }
    }

    suspend fun loadProfile(): UserProfile {
        return api.me(bearer())
    }

    private suspend fun loadDevelopmentProfile(): UserProfile =
        api.developmentMe(bearer()).asAcceptanceProfile()

    suspend fun updateProfile(name: String?, country: String?, languages: List<String>): UserProfile {
        return api.updateMe(bearer(), UserUpdateRequest(name, country, languages))
    }

    suspend fun updateTesterEmail(email: String, consent: Boolean): UserProfile {
        return api.updateTesterEmail(bearer(), TesterEmailRequest(email, consent))
    }

    suspend fun updateDevice(body: DeviceUpdateRequest) {
        api.updateDevice(bearer(), body)
    }

    suspend fun logout() {
        tokenStore.refreshToken?.let { runCatching { api.logout(LogoutRequest(it)) } }
        tokenStore.clear()
    }

    private fun bearer(): String {
        val access = checkNotNull(tokenStore.accessToken) { "No access token" }
        return "Bearer $access"
    }
}

private fun DevelopmentUser.asAcceptanceProfile() = UserProfile(
    id = id,
    login_email = email,
    display_name = display_name,
    tester_email = email,
    tester_email_sharing_consent = true,
    country = country ?: "CA",
    languages = listOf("en"),
    profile_ready = true,
)
