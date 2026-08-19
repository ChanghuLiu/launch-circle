package com.launchcircle.testers.feature.onboarding

import com.launchcircle.testers.core.model.UserProfile

enum class AppDestination { SIGN_IN, PROFILE, HOME }

object AppFlow {
    fun destination(profile: UserProfile?): AppDestination = when {
        profile == null -> AppDestination.SIGN_IN
        else -> AppDestination.HOME
    }
}
