package com.launchcircle.testers.core.storage

import android.content.Context

class TokenStore(context: Context) {
    private val preferences = context.getSharedPreferences("launch_circle_session", Context.MODE_PRIVATE)

    var accessToken: String?
        get() = preferences.getString("access_token", null)
        private set(value) = preferences.edit().putString("access_token", value).apply()

    var refreshToken: String?
        get() = preferences.getString("refresh_token", null)
        private set(value) = preferences.edit().putString("refresh_token", value).apply()

    var authMode: String?
        get() = preferences.getString("auth_mode", null)
        private set(value) = preferences.edit().putString("auth_mode", value).apply()

    fun save(access: String, refresh: String, mode: String = "google") {
        accessToken = access
        refreshToken = refresh
        authMode = mode
    }

    fun clear() {
        preferences.edit().clear().apply()
    }
}
