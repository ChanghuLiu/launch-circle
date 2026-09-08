package com.launchcircle.testers.core.launch

import com.launchcircle.testers.core.model.CreateAppRequest
import com.launchcircle.testers.core.model.FeedbackRequest
import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchDashboard
import com.launchcircle.testers.core.model.LaunchInvite
import com.launchcircle.testers.core.model.LaunchCircle
import com.launchcircle.testers.core.model.MissionFeedback
import com.launchcircle.testers.core.model.PilotConfig
import com.launchcircle.testers.core.model.MatchingResult
import com.launchcircle.testers.core.model.TestMission
import com.launchcircle.testers.core.model.TestAssignment
import com.launchcircle.testers.core.model.TesterAssignment
import com.launchcircle.testers.core.network.LaunchCircleApi
import com.launchcircle.testers.core.storage.TokenStore
import retrofit2.HttpException

interface LaunchRepository {
    suspend fun pilotConfig(): PilotConfig
    suspend fun launches(): List<LaunchApp>
    suspend fun createApp(request: CreateAppRequest): LaunchApp
    suspend fun dashboard(appId: String): LaunchDashboard
    suspend fun circle(appId: String): LaunchCircle
    suspend fun confirmGoogleGroup(appId: String): LaunchApp
    suspend fun matchTesters(appId: String): MatchingResult
    suspend fun testers(appId: String): List<TesterAssignment>
    suspend fun feedback(appId: String): List<MissionFeedback>
    suspend fun todaysMissions(): List<TestMission>
    suspend fun todaysAssignments(): List<TestAssignment>
    suspend fun completeAssignment(assignmentId: String): TestAssignment
    suspend fun missions(assignmentId: String): List<TestMission>
    suspend fun optIn(assignmentId: String): TesterAssignment
    suspend fun installed(assignmentId: String): TesterAssignment
    suspend fun startMission(missionId: String): TestMission
    suspend fun completeMission(missionId: String): TestMission
    suspend fun submitFeedback(missionId: String, request: FeedbackRequest): MissionFeedback
    suspend fun createInvite(appId: String): LaunchInvite
    suspend fun acceptInvite(inviteCode: String): LaunchInvite
}

class RealLaunchRepository(
    private val api: LaunchCircleApi,
    private val tokenStore: TokenStore,
    private val refreshSession: suspend () -> Boolean,
) : LaunchRepository {
    private fun bearer(): String =
        "Bearer " + checkNotNull(tokenStore.accessToken) { "No access token" }

    private suspend fun <T> authenticated(request: suspend (String) -> T): T {
        return try {
            request(bearer())
        } catch (error: HttpException) {
            if (error.code() != 401 || !refreshSession()) throw error
            request(bearer())
        }
    }

    override suspend fun pilotConfig() = api.pilotConfig()
    override suspend fun launches() = authenticated { api.apps(it) }
    override suspend fun createApp(request: CreateAppRequest) = authenticated { api.createApp(it, request) }
    override suspend fun dashboard(appId: String) = authenticated { api.dashboard(it, appId) }
    override suspend fun circle(appId: String) = authenticated { api.appCircle(it, appId) }
    override suspend fun confirmGoogleGroup(appId: String) = authenticated { api.confirmGoogleGroup(it, appId) }
    override suspend fun matchTesters(appId: String) = authenticated { api.matchTesters(it, appId) }
    override suspend fun testers(appId: String) = authenticated { api.testers(it, appId) }
    override suspend fun feedback(appId: String) = authenticated { api.feedback(it, appId) }
    override suspend fun todaysMissions() = authenticated { api.todaysMissions(it) }
    override suspend fun todaysAssignments() = authenticated { api.todaysAssignments(it) }
    override suspend fun completeAssignment(assignmentId: String) =
        authenticated { api.completeAssignment(it, assignmentId) }
    override suspend fun missions(assignmentId: String) = authenticated { api.missions(it, assignmentId) }
    override suspend fun optIn(assignmentId: String) = authenticated { api.optIn(it, assignmentId) }
    override suspend fun installed(assignmentId: String) = authenticated { api.installed(it, assignmentId) }
    override suspend fun startMission(missionId: String) = authenticated { api.startMission(it, missionId) }
    override suspend fun completeMission(missionId: String) = authenticated { api.completeMission(it, missionId) }
    override suspend fun submitFeedback(missionId: String, request: FeedbackRequest) =
        authenticated { api.submitFeedback(it, missionId, request) }
    override suspend fun createInvite(appId: String) = authenticated { api.createAppInvite(it, appId) }
    override suspend fun acceptInvite(inviteCode: String) = authenticated { api.acceptInvite(it, inviteCode) }
}
