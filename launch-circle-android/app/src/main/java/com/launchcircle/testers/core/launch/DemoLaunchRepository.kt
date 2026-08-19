package com.launchcircle.testers.core.launch

import com.launchcircle.testers.core.model.CreateAppRequest
import com.launchcircle.testers.core.model.FeedbackRequest
import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchDashboard
import com.launchcircle.testers.core.model.LaunchInvite
import com.launchcircle.testers.core.model.MatchingResult
import com.launchcircle.testers.core.model.MissionFeedback
import com.launchcircle.testers.core.model.PilotConfig
import com.launchcircle.testers.core.model.TestMission
import com.launchcircle.testers.core.model.TesterAssignment

class DemoLaunchRepository : LaunchRepository {
    private val config = PilotConfig()
    private val apps = mutableListOf(
        demoApp("cold", "Fresh Launch", "WAITING_FOR_TESTERS"),
        demoApp("early", "eSIM Checker", "WAITING_FOR_TESTERS"),
        demoApp("healthy", "BLE Signal Analyzer", "TESTING", "2026-08-14T00:00:00Z"),
        demoApp("risk", "Privacy Scanner", "AT_RISK", "2026-08-14T00:00:00Z"),
        demoApp("ready", "Notes Escape", "PRODUCTION_READY", "2026-08-01T00:00:00Z", true),
    )
    private var todays = mutableListOf(
        TestMission(
            "mission-1", "assignment-1", "notes", "Notes Escape",
            "https://play.google.com/apps/testing/com.demo.notes", "CORE_FEATURE",
            3, "AVAILABLE", null, null, 5, "ACTIVE",
        ),
        TestMission(
            "mission-2", "assignment-2", "camera", "Hidden Camera Detector",
            "https://play.google.com/apps/testing/com.demo.camera", "INSTALL_FIRST_IMPRESSION",
            1, "AVAILABLE", null, null, 3,
        ),
    )
    private val feedbackRows = mutableListOf<MissionFeedback>()
    private var invite = LaunchInvite(
        "invite-1", "LC-8H4K2", "PENDING",
        "https://launchcircle.app/join/LC-8H4K2",
    )

    override suspend fun pilotConfig() = config
    override suspend fun launches() = apps.toList()

    override suspend fun createApp(request: CreateAppRequest): LaunchApp {
        val app = LaunchApp(
            id = "demo-" + (apps.size + 1),
            owner_id = "demo-owner",
            name = request.name,
            package_name = request.package_name,
            opt_in_url = request.opt_in_url,
            google_group_url = request.google_group_url ?: config.google_group_join_url,
            status = "WAITING_FOR_TESTERS",
            tester_target = 15,
            testing_start_at = null,
            testing_end_at = null,
            google_group_mode = request.google_group_mode,
        )
        apps.add(0, app)
        return app
    }

    override suspend fun dashboard(appId: String): LaunchDashboard = when (appId) {
        "cold" -> dashboard("WAITING_FOR_TESTERS", 0, 0, 0, 15, 0)
        "early" -> dashboard("WAITING_FOR_TESTERS", 5, 5, 32, 9, 0)
        "healthy" -> dashboard("TESTING", 13, 15, 64, 8, 6, missions = 21, available = 25)
        "risk" -> dashboard("AT_RISK", 12, 15, 55, 8, 6, risk = 2, replacements = 1)
        "ready" -> dashboard("PRODUCTION_READY", 13, 15, 100, 0, 14, missions = 78, available = 78)
        else -> dashboard("WAITING_FOR_TESTERS", 0, 0, 15, 14, 0)
    }

    override suspend fun confirmGoogleGroup(appId: String): LaunchApp {
        val index = apps.indexOfFirst { it.id == appId }
        val updated = apps[index].copy(
            google_group_configured = true,
            google_group_confirmed_at = "2026-08-19T12:00:00Z",
        )
        apps[index] = updated
        return updated
    }

    override suspend fun matchTesters(appId: String) =
        MatchingResult(2, 15, 13, 0, 15, 0)

    override suspend fun testers(appId: String): List<TesterAssignment> = listOf(
        assignment("18", appId, "ACTIVE", "GOOD", 4, 6),
        assignment("22", appId, "ASSIGNED", "NEW", 0, 0),
        assignment("31", appId, "ACTIVE", "AT_RISK", 2, 4),
        assignment("40", appId, "ACTIVE", "INACTIVE", 1, 4),
        assignment("44", appId, "DROPPED", "DROPPED", 2, 3),
        assignment("51", appId, "ACTIVE", "GOOD", 1, 2, true, "assignment-44"),
    )

    override suspend fun feedback(appId: String) = feedbackRows.filter { it.app_id == appId }
    override suspend fun todaysMissions() = todays.toList()
    override suspend fun missions(assignmentId: String) =
        todays.filter { it.assignment_id == assignmentId }

    override suspend fun optIn(assignmentId: String) =
        assignment("18", "notes", "OPTED_IN", "NEW", 0, 0).copy(id = assignmentId)

    override suspend fun installed(assignmentId: String) =
        assignment("18", "notes", "ACTIVE", "GOOD", 0, 6).copy(id = assignmentId)

    override suspend fun startMission(missionId: String) = todays.first { it.id == missionId }

    override suspend fun completeMission(missionId: String): TestMission {
        val mission = todays.first { it.id == missionId }.copy(status = "COMPLETED")
        todays = todays.filterNot { it.id == missionId }.toMutableList()
        return mission
    }

    override suspend fun submitFeedback(
        missionId: String,
        request: FeedbackRequest,
    ): MissionFeedback {
        val row = MissionFeedback(
            "feedback-" + (feedbackRows.size + 1), missionId, "Tester #DEMO",
            "notes", "CORE_FEATURE", request.launch_ok,
            request.core_feature_ok, request.rating, request.issue_text,
            request.suggestion_text, "2026-08-19T12:00:00Z",
        )
        feedbackRows += row
        return row
    }

    override suspend fun createInvite() = invite

    override suspend fun acceptInvite(inviteCode: String): LaunchInvite {
        require(InviteCodeValidator.isValid(inviteCode)) { "Enter a valid invite code" }
        invite = invite.copy(invite_code = InviteCodeValidator.normalize(inviteCode), status = "ACCEPTED")
        return invite
    }

    private fun demoApp(
        id: String,
        name: String,
        status: String,
        start: String? = null,
        groupConfigured: Boolean = false,
    ) = LaunchApp(
        id, "demo-owner", name, "com.demo.$id",
        "https://play.google.com/apps/testing/com.demo.$id",
        config.google_group_join_url, status, 15, start, null,
        google_group_configured = groupConfigured,
    )

    private fun dashboard(
        status: String,
        active: Int,
        assigned: Int,
        readiness: Int,
        remaining: Int,
        day: Int,
        risk: Int = 0,
        replacements: Int = 0,
        missions: Int = 0,
        available: Int = 0,
    ) = LaunchDashboard(
        status, active, assigned, 15, 12, maxOf(0, 12 - active), day, 14,
        readiness, 0, risk, feedbackRows.size, missions, "2026-09-02",
        "Readiness is guidance only and does not guarantee Google Play production approval.",
        continuous_qualifying_testers = maxOf(0, active - replacements),
        replacement_testers = replacements,
        days_remaining = remaining,
        circle_health = if (risk > 0) "AT_RISK" else "GOOD",
        missions_completed = missions,
        missions_total_available = available,
    )

    private fun assignment(
        suffix: String,
        appId: String,
        status: String,
        health: String,
        completed: Int,
        total: Int,
        replacement: Boolean = false,
        replacementFor: String? = null,
    ) = TesterAssignment(
        "assignment-$suffix", appId, "tester-$suffix", "Tester #$suffix", status,
        "2026-08-13T00:00:00Z", "2026-08-13T01:00:00Z",
        if (status in setOf("ACTIVE", "COMPLETED")) "2026-08-13T02:00:00Z" else null,
        null, completed, total, health, replacement, replacementFor, null,
        if (total > 0) 6 else 0,
    )
}

object InviteCodeValidator {
    private val pattern = Regex("^LC-[A-Z0-9]{5}$")

    fun normalize(value: String): String = value.trim().uppercase()
    fun isValid(value: String): Boolean = pattern.matches(normalize(value))
}
