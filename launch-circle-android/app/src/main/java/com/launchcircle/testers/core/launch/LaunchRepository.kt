package com.launchcircle.testers.core.launch

import com.launchcircle.testers.core.model.CreateAppRequest
import com.launchcircle.testers.core.model.AdditionalAppCheckout
import com.launchcircle.testers.core.model.AdditionalAppCheckoutRequest
import com.launchcircle.testers.core.model.GooglePlayPurchaseVerification
import com.launchcircle.testers.core.model.FeedbackRequest
import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchDashboard
import com.launchcircle.testers.core.model.LaunchInvite
import com.launchcircle.testers.core.model.LaunchCircle
import com.launchcircle.testers.core.model.MissionFeedback
import com.launchcircle.testers.core.model.PilotConfig
import com.launchcircle.testers.core.model.MatchingResult
import com.launchcircle.testers.core.model.WorkloadSummary
import com.launchcircle.testers.core.model.ManagedOfferSummary
import com.launchcircle.testers.core.model.ManagedCheckout
import com.launchcircle.testers.core.model.CoordinationTimeRequest
import com.launchcircle.testers.core.model.ManagedOfferViewRequest
import com.launchcircle.testers.core.model.TestMission
import com.launchcircle.testers.core.model.TestAssignment
import com.launchcircle.testers.core.model.TesterAssignment
import com.launchcircle.testers.core.network.LaunchCircleApi
import com.launchcircle.testers.core.storage.TokenStore
import retrofit2.HttpException

interface LaunchRepository {
    suspend fun evidenceSummary(appId: String): com.launchcircle.testers.core.model.CampaignEvidenceSummary = error("Evidence pilot is not supported")
    suspend fun setEvidenceBuild(appId: String, version: Int, description: String): Unit = error("Evidence pilot is not supported")
    suspend fun declareEvidenceFix(runId: String, version: Int, description: String): Unit = error("Evidence pilot is not supported")

    suspend fun evidenceAssignmentStatus(assignmentId: String): String = error("Evidence pilot is not supported")

    suspend fun evidenceContext(missionId: String): com.launchcircle.testers.core.model.MissionEvidenceContext = error("Evidence pilot is not supported")
    suspend fun submitMissionRun(missionId: String, request: com.launchcircle.testers.core.model.MissionRunRequest): com.launchcircle.testers.core.model.MissionRunRecord = error("Evidence pilot is not supported")
    suspend fun recordEnrollmentEvidence(assignmentId: String): Unit = error("Evidence pilot is not supported")

    suspend fun pilotConfig(): PilotConfig
    suspend fun launches(): List<LaunchApp>
    suspend fun createApp(request: CreateAppRequest): LaunchApp
    suspend fun createAdditionalAppCheckout(developerAccountId: String): AdditionalAppCheckout
    suspend fun additionalAppCheckout(purchaseId: String): AdditionalAppCheckout
    suspend fun createManagedCheckout(appId: String): ManagedCheckout
    suspend fun managedCheckout(checkoutId: String): ManagedCheckout
    suspend fun verifyGooglePlayPurchase(purchaseId: String, purchaseType: String, purchaseToken: String)
    suspend fun dashboard(appId: String): LaunchDashboard
    suspend fun recordCoordinationTime(appId: String, minutes: Int, category: String): WorkloadSummary
    suspend fun recordManagedOfferViewed(appId: String, trigger: String): ManagedOfferSummary
    suspend fun circle(appId: String): LaunchCircle
    suspend fun circles(): List<LaunchCircle>
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
    suspend fun createCircleInvite(): LaunchInvite
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

    override suspend fun evidenceSummary(appId: String) = authenticated { api.evidenceSummary(it, appId) }
    override suspend fun setEvidenceBuild(appId: String, version: Int, description: String) = authenticated {
        api.setEvidenceBuild(it, appId, com.launchcircle.testers.core.model.EvidenceBuildRequest(version, description))
        Unit
    }
    override suspend fun declareEvidenceFix(runId: String, version: Int, description: String) = authenticated {
        api.declareEvidenceFix(it, runId, com.launchcircle.testers.core.model.EvidenceBuildRequest(version, description))
        Unit
    }
    override suspend fun evidenceAssignmentStatus(assignmentId: String) = authenticated {
        api.evidenceAssignmentStatus(it, assignmentId).assignment_status
    }
    override suspend fun evidenceContext(missionId: String) = authenticated { api.evidenceContext(it, missionId) }
    override suspend fun submitMissionRun(missionId: String, request: com.launchcircle.testers.core.model.MissionRunRequest) = authenticated {
        api.submitMissionRun(it, missionId, request.copy(
            device_key = tokenStore.evidenceDeviceKey(),
            device_model = android.os.Build.MODEL,
            android_api = android.os.Build.VERSION.SDK_INT,
        ))
    }
    override suspend fun recordEnrollmentEvidence(assignmentId: String) = authenticated {
        api.recordEnrollmentEvidence(it, assignmentId,
            com.launchcircle.testers.core.model.EnrollmentEvidenceRequest(
                event = "JOINED", note = "Tester confirmed joining through the Play testing link",
            ))
        Unit
    }
    override suspend fun pilotConfig() = api.pilotConfig()
    override suspend fun launches() = authenticated { api.apps(it) }
    override suspend fun createApp(request: CreateAppRequest) = authenticated { api.createApp(it, request) }
    override suspend fun createAdditionalAppCheckout(developerAccountId: String) = authenticated {
        api.createAdditionalAppCheckout(it, AdditionalAppCheckoutRequest(developerAccountId))
    }
    override suspend fun additionalAppCheckout(purchaseId: String) =
        authenticated { api.additionalAppCheckout(it, purchaseId) }
    override suspend fun createManagedCheckout(appId: String) =
        authenticated { api.createManagedCheckout(it, appId) }
    override suspend fun managedCheckout(checkoutId: String) =
        authenticated { api.managedCheckout(it, checkoutId) }
    override suspend fun verifyGooglePlayPurchase(purchaseId: String, purchaseType: String, purchaseToken: String) =
        authenticated {
            api.verifyGooglePlayPurchase(it, GooglePlayPurchaseVerification(purchaseId, purchaseType, purchaseToken))
            Unit
        }
    override suspend fun dashboard(appId: String) = authenticated { api.dashboard(it, appId) }
    override suspend fun recordCoordinationTime(appId: String, minutes: Int, category: String) =
        authenticated { api.recordCoordinationTime(it, appId, CoordinationTimeRequest(minutes, category)) }
    override suspend fun recordManagedOfferViewed(appId: String, trigger: String) =
        authenticated { api.recordManagedOfferViewed(it, appId, ManagedOfferViewRequest(trigger)) }
    override suspend fun circle(appId: String) = authenticated { api.appCircle(it, appId) }
    override suspend fun circles() = authenticated { api.circles(it) }
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
    override suspend fun createCircleInvite() = authenticated { api.createInvite(it) }
    override suspend fun createInvite(appId: String) = authenticated { api.createAppInvite(it, appId) }
    override suspend fun acceptInvite(inviteCode: String) = authenticated { api.acceptInvite(it, inviteCode) }
}
