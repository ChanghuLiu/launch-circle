package com.launchcircle.testers.core.storage

import android.content.Context
import android.content.SharedPreferences
import com.android.installreferrer.api.InstallReferrerClient
import com.android.installreferrer.api.InstallReferrerStateListener
import com.launchcircle.testers.core.model.InstallAttribution
import java.net.URLDecoder
import java.nio.charset.StandardCharsets
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.coroutines.resume

internal object InstallAttributionParser {
    fun parse(referrer: String): InstallAttribution? {
        val values = referrer.take(4_000).removePrefix("?")
            .split("&")
            .mapNotNull { parameter ->
                val parts = parameter.split("=", limit = 2)
                if (parts.size != 2) return@mapNotNull null
                val key = decode(parts[0]) ?: return@mapNotNull null
                val value = decode(parts[1]) ?: return@mapNotNull null
                key to value
            }
            .toMap()
        val source = normalize(values["utm_source"]) ?: return null
        return InstallAttribution(
            source = source,
            medium = normalize(values["utm_medium"]),
            campaign = normalize(values["utm_campaign"]),
        )
    }

    private fun decode(value: String): String? = runCatching {
        URLDecoder.decode(value, StandardCharsets.UTF_8.name())
    }.getOrNull()

    private fun normalize(value: String?): String? = value
        ?.trim()
        ?.lowercase()
        ?.map { char ->
            when {
                char in 'a'..'z' || char in '0'..'9' || char in "._-" -> char
                char.isWhitespace() -> '-'
                else -> null
            }
        }
        ?.filterNotNull()
        ?.joinToString("")
        ?.take(120)
        ?.takeIf(String::isNotBlank)
}

class InstallAttributionStore(context: Context) {
    private val preferences: SharedPreferences =
        context.applicationContext.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    fun current(): InstallAttribution? {
        val source = preferences.getString(KEY_SOURCE, null)?.takeIf(String::isNotBlank)
            ?: return null
        return InstallAttribution(
            source = source,
            medium = preferences.getString(KEY_MEDIUM, null),
            campaign = preferences.getString(KEY_CAMPAIGN, null),
        )
    }

    fun saveIfMissing(attribution: InstallAttribution) {
        if (preferences.getString(KEY_SOURCE, null).isNullOrBlank()) {
            preferences.edit()
                .putString(KEY_SOURCE, attribution.source)
                .putString(KEY_MEDIUM, attribution.medium)
                .putString(KEY_CAMPAIGN, attribution.campaign)
                .apply()
        }
    }

    private companion object {
        const val PREFERENCES_NAME = "launch_circle_attribution"
        const val KEY_SOURCE = "source"
        const val KEY_MEDIUM = "medium"
        const val KEY_CAMPAIGN = "campaign"
    }
}

class PlayInstallAttributionReader(
    context: Context,
    private val store: InstallAttributionStore,
) {
    private val appContext = context.applicationContext

    suspend fun fetch(): InstallAttribution? {
        store.current()?.let { return it }
        return withTimeoutOrNull(2_000) {
            suspendCancellableCoroutine { continuation ->
                val client = InstallReferrerClient.newBuilder(appContext).build()
                val finish = {
                    runCatching { client.endConnection() }
                    if (continuation.isActive) continuation.resume(store.current())
                }
                continuation.invokeOnCancellation {
                    runCatching { client.endConnection() }
                }
                try {
                    client.startConnection(object : InstallReferrerStateListener {
                        override fun onInstallReferrerSetupFinished(responseCode: Int) {
                            try {
                                if (responseCode == InstallReferrerClient.InstallReferrerResponse.OK) {
                                    InstallAttributionParser.parse(client.installReferrer.installReferrer)
                                        ?.let(store::saveIfMissing)
                                }
                            } catch (_: Exception) {
                                // Attribution is optional; sign-in and app setup must remain available.
                            } finally {
                                finish()
                            }
                        }

                        override fun onInstallReferrerServiceDisconnected() {
                            finish()
                        }
                    })
                } catch (_: Exception) {
                    finish()
                }
            }
        } ?: store.current()
    }
}
