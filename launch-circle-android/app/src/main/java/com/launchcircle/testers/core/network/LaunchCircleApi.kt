package com.launchcircle.testers.core.network

import com.launchcircle.testers.core.model.DeviceUpdateRequest
import com.launchcircle.testers.core.model.DevelopmentLoginRequest
import com.launchcircle.testers.core.model.DevelopmentUser
import com.launchcircle.testers.core.model.CreateAppRequest
import com.launchcircle.testers.core.model.FeedbackRequest
import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchDashboard
import com.launchcircle.testers.core.model.LaunchInvite
import com.launchcircle.testers.core.model.MissionFeedback
import com.launchcircle.testers.core.model.MatchingResult
import com.launchcircle.testers.core.model.TestMission
import com.launchcircle.testers.core.model.TesterAssignment
import com.launchcircle.testers.core.model.InviteRequest
import com.launchcircle.testers.core.model.GoogleAuthRequest
import com.launchcircle.testers.core.model.GoogleGroupConfirmationRequest
import com.launchcircle.testers.core.model.PilotConfig
import com.launchcircle.testers.core.model.LogoutRequest
import com.launchcircle.testers.core.model.RefreshRequest
import com.launchcircle.testers.core.model.TesterEmailRequest
import com.launchcircle.testers.core.model.TokenPair
import com.launchcircle.testers.core.model.UserProfile
import com.launchcircle.testers.core.model.UserUpdateRequest
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.PATCH
import retrofit2.http.Path
import retrofit2.http.PUT

interface LaunchCircleApi {
    @GET("pilot-config")
    suspend fun pilotConfig(): PilotConfig

    @POST("auth/login")
    suspend fun developmentLogin(@Body body: DevelopmentLoginRequest): TokenPair

    @GET("me")
    suspend fun developmentMe(@Header("Authorization") authorization: String): DevelopmentUser

    @POST("v1/auth/google")
    suspend fun googleAuth(@Body body: GoogleAuthRequest): TokenPair

    @POST("v1/auth/refresh")
    suspend fun refresh(@Body body: RefreshRequest): TokenPair

    @POST("v1/auth/logout")
    suspend fun logout(@Body body: LogoutRequest)

    @GET("v1/me")
    suspend fun me(@Header("Authorization") authorization: String): UserProfile

    @PUT("v1/me")
    suspend fun updateMe(
        @Header("Authorization") authorization: String,
        @Body body: UserUpdateRequest,
    ): UserProfile

    @PUT("v1/me/tester-email")
    suspend fun updateTesterEmail(
        @Header("Authorization") authorization: String,
        @Body body: TesterEmailRequest,
    ): UserProfile

    @PUT("v1/me/device")
    suspend fun updateDevice(
        @Header("Authorization") authorization: String,
        @Body body: DeviceUpdateRequest,
    ): Map<String, Any>

    @GET("apps")
    suspend fun apps(@Header("Authorization") authorization: String): List<LaunchApp>

    @POST("apps")
    suspend fun createApp(@Header("Authorization") authorization: String, @Body body: CreateAppRequest): LaunchApp

    @POST("apps/{appId}/google-group/confirm")
    suspend fun confirmGoogleGroup(@Header("Authorization") authorization: String, @Path("appId") appId: String, @Body body: GoogleGroupConfirmationRequest = GoogleGroupConfirmationRequest()): LaunchApp

    @GET("apps/{appId}/dashboard")
    suspend fun dashboard(@Header("Authorization") authorization: String, @Path("appId") appId: String): LaunchDashboard

    @POST("apps/{appId}/match-testers")
    suspend fun matchTesters(@Header("Authorization") authorization: String, @Path("appId") appId: String): MatchingResult

    @GET("apps/{appId}/testers")
    suspend fun testers(@Header("Authorization") authorization: String, @Path("appId") appId: String): List<TesterAssignment>

    @GET("apps/{appId}/feedback")
    suspend fun feedback(@Header("Authorization") authorization: String, @Path("appId") appId: String): List<MissionFeedback>

    @GET("test-missions/today")
    suspend fun todaysMissions(@Header("Authorization") authorization: String): List<TestMission>

    @GET("assignments/{assignmentId}/missions")
    suspend fun missions(@Header("Authorization") authorization: String, @Path("assignmentId") assignmentId: String): List<TestMission>

    @PATCH("assignments/{assignmentId}/opt-in")
    suspend fun optIn(@Header("Authorization") authorization: String, @Path("assignmentId") assignmentId: String): TesterAssignment

    @PATCH("assignments/{assignmentId}/installed")
    suspend fun installed(@Header("Authorization") authorization: String, @Path("assignmentId") assignmentId: String): TesterAssignment

    @POST("missions/{missionId}/start")
    suspend fun startMission(@Header("Authorization") authorization: String, @Path("missionId") missionId: String): TestMission

    @PATCH("missions/{missionId}/complete")
    suspend fun completeMission(@Header("Authorization") authorization: String, @Path("missionId") missionId: String): TestMission

    @POST("missions/{missionId}/feedback")
    suspend fun submitFeedback(@Header("Authorization") authorization: String, @Path("missionId") missionId: String, @Body body: FeedbackRequest): MissionFeedback

    @POST("invites/{inviteCode}/accept")
    suspend fun acceptInvite(@Header("Authorization") authorization: String, @Path("inviteCode") inviteCode: String): LaunchInvite

    @POST("invites")
    suspend fun createInvite(@Header("Authorization") authorization: String, @Body body: InviteRequest = InviteRequest()): LaunchInvite
}
