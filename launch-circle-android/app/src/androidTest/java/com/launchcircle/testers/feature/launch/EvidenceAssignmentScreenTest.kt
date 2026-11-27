package com.launchcircle.testers.feature.launch

import androidx.activity.ComponentActivity
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.platform.UriHandler
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.launchcircle.testers.R
import com.launchcircle.testers.core.model.TestAssignment
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class EvidenceAssignmentScreenTest {
    @get:Rule
    val compose = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun sharedGroupMustBeReadyBeforeAppPlayOptInIsShown() {
        setAssignmentScreen(groupReady = false)

        compose.onNodeWithText("Complete the group step above", substring = true).assertExists()
        assertEquals(
            0,
            compose.onAllNodesWithText(compose.activity.getString(R.string.open_play_testing_link)).fetchSemanticsNodes().size,
        )
        assertEquals(
            0,
            compose.onAllNodesWithText(compose.activity.getString(R.string.confirm_opt_in)).fetchSemanticsNodes().size,
        )
    }

    @Test
    fun appPlayOptInRequiresOpeningItsLinkAndConfirming() {
        var openedUri: String? = null
        var confirmed = false
        setAssignmentScreen(
            groupReady = true,
            onUriOpened = { openedUri = it },
            onOptIn = { confirmed = true },
        )

        val openLink = compose.activity.getString(R.string.open_play_testing_link)
        val confirmOptIn = compose.activity.getString(R.string.confirm_opt_in)
        compose.onNodeWithText(confirmOptIn).assertIsNotEnabled()
        compose.onNodeWithText(openLink).performClick()
        compose.onNodeWithText(confirmOptIn).assertIsEnabled().performClick()

        assertEquals("https://play.google.com/apps/testing/com.example.target", openedUri)
        assertEquals(true, confirmed)
    }

    @Test
    fun appSpecificGroupMustBeConfirmedBeforePlayOptIn() {
        setAssignmentScreen(
            groupReady = true,
            appGroupUrl = "https://groups.google.com/g/app-specific-group",
        )

        compose.onNodeWithText("This app also needs its own Google Group").assertExists()
        val openLink = compose.activity.getString(R.string.open_play_testing_link)
        compose.onNodeWithText(openLink).assertIsNotEnabled()
        compose.onNodeWithText("I have joined this group").performClick()
        compose.onNodeWithText(openLink).assertIsEnabled()
    }

    private fun setAssignmentScreen(
        groupReady: Boolean,
        appGroupUrl: String? = null,
        onUriOpened: (String) -> Unit = {},
        onOptIn: () -> Unit = {},
    ) {
        compose.setContent {
            CompositionLocalProvider(
                LocalUriHandler provides object : UriHandler {
                    override fun openUri(uri: String) = onUriOpened(uri)
                },
            ) {
                MaterialTheme {
                    EvidenceAssignmentScreen(
                        assignment = sampleAssignment(appGroupUrl),
                        missions = emptyList(),
                        loading = false,
                        groupReady = groupReady,
                        sharedGroupUrl = "https://groups.google.com/g/launch-circle-12-testers",
                        accessCard = {},
                        onOptIn = onOptIn,
                        onInstalled = {},
                        onMission = {},
                    )
                }
            }
        }
    }

    private fun sampleAssignment(appGroupUrl: String?) = TestAssignment(
        id = "assignment-1",
        circle_id = "group-1",
        app_id = "app-1",
        app_name = "Sample app",
        package_name = "com.example.target",
        opt_in_url = "https://play.google.com/apps/testing/com.example.target",
        test_type = "COLD_START",
        status = "ASSIGNED",
        assignment_day = "2026-11-27",
        assigned_at = "2026-11-27T00:00:00Z",
        completed_at = null,
        google_group_url = appGroupUrl,
    )
}
