package com.launchcircle.testers.core.auth

import com.launchcircle.testers.core.model.DeviceUpdateRequest
import com.launchcircle.testers.core.model.InstallAttribution
import com.launchcircle.testers.core.model.GoogleAuthRequest
import com.launchcircle.testers.core.model.LogoutRequest
import com.launchcircle.testers.core.model.RefreshRequest
import com.launchcircle.testers.core.model.TesterEmailRequest
import com.launchcircle.testers.core.model.UserProfile
import com.launchcircle.testers.core.model.UserUpdateRequest
import com.launchcircle.testers.core.network.LaunchCircleApi
import com.launchcircle.testers.core.storage.TokenStore
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import retrofit2.HttpException

class AuthRepository(
    private val api: LaunchCircleApi,
    private val tokenStore: TokenStore,
    private val installAttribution: suspend () -> InstallAttribution? = { null },
) {
    private val refreshMutex = Mutex()

    fun clearSession() = tokenStore.clear()

    suspend fun exchangeGoogleToken(idToken: String): UserProfile {
        val attribution = installAttribution()
        val tokens = api.googleAuth(
            GoogleAuthRequest(
                id_token = idToken,
                acquisition_source = attribution?.source,
                acquisition_medium = attribution?.medium,
                acquisition_campaign = attribution?.campaign,
            ),
        )
        tokenStore.save(tokens.access_token, tokens.refresh_token)
        return loadProfile()
    }

    suspend fun restoreSession(): UserProfile? {
        if (!refreshSession()) return null
        return try {
            loadProfile()
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (failure: HttpException) {
            if (failure.code() == 401) tokenStore.clear()
            null
        } catch (_: Exception) {
            null
        }
    }

    suspend fun refreshSession(): Boolean = refreshMutex.withLock {
        val refresh = tokenStore.refreshToken ?: return@withLock false
        try {
            val tokens = api.refresh(RefreshRequest(refresh))
            tokenStore.save(tokens.access_token, tokens.refresh_token)
            true
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (failure: HttpException) {
            if (failure.code() == 401) tokenStore.clear()
            false
        } catch (_: Exception) {
            // Keep the refresh token on network/server failures so a transient outage
            // does not force the user to sign in again.
            false
        }
    }

    suspend fun loadProfile(): UserProfile = api.me(bearer())

    suspend fun updateProfile(name: String?, country: String?, languages: List<String>): UserProfile {
        return api.updateMe(bearer(), UserUpdateRequest(name, country, languages))
    }

    suspend fun updateTesterEmail(email: String, consent: Boolean): UserProfile {
        return api.updateTesterEmail(bearer(), TesterEmailRequest(email, consent))
    }

    suspend fun updateDevice(body: DeviceUpdateRequest) {
        api.updateDevice(bearer(), body)
    }

    suspend fun deleteAccount() {
        deleteAccountAndClearSession(
            deleteRemote = { api.deleteMe(bearer()) },
            clearSession = tokenStore::clear,
        )
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
