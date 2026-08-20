package com.launchcircle.testers

import com.launchcircle.testers.core.model.UserProfile
import com.launchcircle.testers.core.model.GoogleAuthRequest
import com.google.gson.Gson
import com.launchcircle.testers.feature.onboarding.AppDestination
import com.launchcircle.testers.feature.onboarding.AppFlow
import org.junit.Assert.assertEquals
import org.junit.Test

class AppFlowTest {
    private fun profile(ready: Boolean) = UserProfile(
        id = "1",
        login_email = "login@example.com",
        display_name = "Tester",
        tester_email = if (ready) "tester@gmail.com" else null,
        tester_email_sharing_consent = ready,
        country = if (ready) "CA" else null,
        languages = if (ready) listOf("en") else emptyList(),
        profile_ready = ready,
    )

    @Test
    fun routesSignedOutToSignIn() {
        assertEquals(AppDestination.SIGN_IN, AppFlow.destination(null))
    }

    @Test
    fun routesSignedInProfileDirectlyHome() {
        assertEquals(AppDestination.HOME, AppFlow.destination(profile(false)))
    }

    @Test
    fun routesReadyProfileToHome() {
        assertEquals(AppDestination.HOME, AppFlow.destination(profile(true)))
    }


    @Test
    fun googleAuthRequestUsesBackendWireField() {
        val json = Gson().toJson(GoogleAuthRequest("token-value"))
        assertEquals("token-value", Gson().fromJson(json, Map::class.java)["id_token"])
    }
}
