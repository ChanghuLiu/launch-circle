package com.launchcircle.testers.core.launch

import com.launchcircle.testers.core.model.CreateAppRequest
import com.launchcircle.testers.core.model.FeedbackRequest
import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchDashboard
import com.launchcircle.testers.core.model.LaunchInvite
import com.launchcircle.testers.core.model.MissionFeedback
import com.launchcircle.testers.core.model.PilotConfig
import com.launchcircle.testers.core.model.MatchingResult
import com.launchcircle.testers.core.model.TestMission
import com.launchcircle.testers.core.model.TesterAssignment
import com.launchcircle.testers.core.network.LaunchCircleApi
import com.launchcircle.testers.core.storage.TokenStore

interface LaunchRepository {
    suspend fun pilotConfig(): PilotConfig
    suspend fun launches(): List<LaunchApp>
    suspend fun createApp(request: CreateAppRequest): LaunchApp
    suspend fun dashboard(appId: String): LaunchDashboard
    suspend fun confirmGoogleGroup(appId: String): LaunchApp
    suspend fun matchTesters(appId: String): MatchingResult
    suspend fun testers(appId: String): List<TesterAssignment>
    suspend fun feedback(appId: String): List<MissionFeedback>
    suspend fun todaysMissions(): List<TestMission>
    suspend fun missions(assignmentId: String): List<TestMission>
    suspend fun optIn(assignmentId: String): TesterAssignment
    suspend fun installed(assignmentId: String): TesterAssignment
    suspend fun startMission(missionId: String): TestMission
    suspend fun completeMission(missionId: String): TestMission
    suspend fun submitFeedback(missionId: String, request: FeedbackRequest): MissionFeedback
    suspend fun createInvite(): LaunchInvite
    suspend fun acceptInvite(inviteCode: String): LaunchInvite
}

class RealLaunchRepository(
    private val api: LaunchCircleApi,
    private val tokenStore: TokenStore,
) : LaunchRepository {
    private fun bearer(): String =
        "Bearer " + checkNotNull(tokenStore.accessToken) { "No access token" }

    override suspend fun pilotConfig() = api.pilotConfig()
    override suspend fun launches() = api.apps(bearer())
    override suspend fun createApp(request: CreateAppRequest) = api.createApp(bearer(), request)
    override suspend fun dashboard(appId: String) = api.dashboard(bearer(), appId)
    override suspend fun confirmGoogleGroup(appId: String) = api.confirmGoogleGroup(bearer(), appId)
    override suspend fun matchTesters(appId: String) = api.matchTesters(bearer(), appId)
    override suspend fun testers(appId: String) = api.testers(bearer(), appId)
    override suspend fun feedback(appId: String) = api.feedback(bearer(), appId)
    override suspend fun todaysMissions() = api.todaysMissions(bearer())
    override suspend fun missions(assignmentId: String) = api.missions(bearer(), assignmentId)
    override suspend fun optIn(assignmentId: String) = api.optIn(bearer(), assignmentId)
    override suspend fun installed(assignmentId: String) = api.installed(bearer(), assignmentId)
    override suspend fun startMission(missionId: String) = api.startMission(bearer(), missionId)
    override suspend fun completeMission(missionId: String) = api.completeMission(bearer(), missionId)
    override suspend fun submitFeedback(missionId: String, request: FeedbackRequest) =
        api.submitFeedback(bearer(), missionId, request)
    override suspend fun createInvite() = api.createInvite(bearer())
    override suspend fun acceptInvite(inviteCode: String) = api.acceptInvite(bearer(), inviteCode)
}
