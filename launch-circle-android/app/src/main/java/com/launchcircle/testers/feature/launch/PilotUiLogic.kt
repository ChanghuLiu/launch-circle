package com.launchcircle.testers.feature.launch

import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchDashboard

object PilotUiLogic {
    fun coldStartMessage(dashboard: LaunchDashboard): String? =
        if (dashboard.testers_needed_for_minimum > 0) {
            "Need " + dashboard.testers_needed_for_minimum + " more to reach the minimum."
        } else {
            null
        }

    fun isGoogleGroupSetupComplete(app: LaunchApp): Boolean =
        app.google_group_configured && app.google_group_confirmed_at != null
}
