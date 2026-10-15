package com.launchcircle.testers.feature.launch

import android.app.Activity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.launchcircle.testers.core.billing.PlayBillingGateway
import com.launchcircle.testers.core.launch.InviteCodeValidator
import com.launchcircle.testers.core.launch.LaunchRepository
import com.launchcircle.testers.core.model.CreateAppRequest
import com.launchcircle.testers.core.model.AdditionalAppCheckout
import com.launchcircle.testers.core.model.ManagedCheckout
import com.launchcircle.testers.core.model.FeedbackRequest
import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchDashboard
import com.launchcircle.testers.core.model.LaunchInvite
import com.launchcircle.testers.core.model.LaunchCircle
import com.launchcircle.testers.core.model.MatchingResult
import com.launchcircle.testers.core.model.MissionFeedback
import com.launchcircle.testers.core.model.PilotConfig
import com.launchcircle.testers.core.model.TestMission
import com.launchcircle.testers.core.model.TestAssignment
import com.launchcircle.testers.core.model.TesterAssignment
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.delay
import retrofit2.HttpException
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class LaunchDestination {
    MY_LAUNCHES, ADD_APP, DASHBOARD, TODAY_TESTS, ASSIGNMENT, MISSION, TESTERS, FEEDBACK, ACCOUNT
}

enum class PilotSurface {
    NONE, INVITE, JOIN, JOIN_SUCCESS, GROUP_SETUP, ADDITIONAL_APP_PAYMENT, MANAGED_PAYMENT
}

data class LaunchUiState(
    val destination: LaunchDestination = LaunchDestination.MY_LAUNCHES,
    val pilotSurface: PilotSurface = PilotSurface.NONE,
    val pilotConfig: PilotConfig = PilotConfig(),
    val launches: List<LaunchApp> = emptyList(),
    val dashboards: Map<String, LaunchDashboard> = emptyMap(),
    val selectedApp: LaunchApp? = null,
    val circle: LaunchCircle? = null,
    val availableCircles: List<LaunchCircle> = emptyList(),
    val selectedMission: TestMission? = null,
    val selectedAssignment: TestAssignment? = null,
    val testers: List<TesterAssignment> = emptyList(),
    val feedback: List<MissionFeedback> = emptyList(),
    val today: List<TestMission> = emptyList(),
    val todayAssignments: List<TestAssignment> = emptyList(),
    val invite: LaunchInvite? = null,
    val pendingPayment: AdditionalAppCheckout? = null,
    val pendingManagedPayment: ManagedCheckout? = null,
    val googlePlayPrice: String? = null,
    val googlePlayListPrice: String? = null,
    val matchingResult: MatchingResult? = null,
    val loading: Boolean = true,
    val error: String? = null,
)

class LaunchViewModel(
    private val repository: LaunchRepository,
) : ViewModel() {

    private var loadedUserId: String? = null
    private var pendingAppRequest: CreateAppRequest? = null
    private var playBillingGateway: PlayBillingGateway? = null
    private var activePurchaseId: String? = null
    private var activePurchaseType: String? = null
    private val _state = MutableStateFlow(LaunchUiState())
    val state: StateFlow<LaunchUiState> = _state.asStateFlow()

    fun loadLaunches(userId: String) {
        if (loadedUserId == userId) return
        loadedUserId = userId
        _state.value = LaunchUiState()
        loadWorkspace()
    }

    fun refresh() {
        if (loadedUserId != null) loadWorkspace()
    }

    private fun loadWorkspace() {
        runTask {
            val config = runCatching { repository.pilotConfig() }.getOrDefault(PilotConfig())
            val apps = repository.launches()
            val dashboards = apps.associate { it.id to repository.dashboard(it.id) }
            val availableCircles = repository.circles()
            val selected = _state.value.selectedApp?.let { current ->
                apps.firstOrNull { it.id == current.id }
            } ?: apps.firstOrNull()
            val circle = selected?.let { repository.circle(it.id) }
            _state.value.copy(
                destination = if (selected == null) {
                    LaunchDestination.MY_LAUNCHES
                } else {
                    _state.value.destination
                },
                pilotConfig = config,
                launches = apps,
                dashboards = dashboards,
                selectedApp = selected,
                circle = circle,
                availableCircles = availableCircles,
                todayAssignments = repository.todaysAssignments(),
            )
        }
    }

    fun showHome() {
        val app = _state.value.selectedApp ?: _state.value.launches.firstOrNull()
        if (app == null) {
            _state.value = _state.value.copy(destination = LaunchDestination.MY_LAUNCHES)
        } else {
            showDashboard(app)
        }
    }

    fun showMyLaunch() {
        _state.value = _state.value.copy(
            destination = LaunchDestination.MY_LAUNCHES,
            pilotSurface = PilotSurface.NONE,
            error = null,
        )
    }

    fun showAccount() {
        _state.value = _state.value.copy(
            destination = LaunchDestination.ACCOUNT,
            pilotSurface = PilotSurface.NONE,
            error = null,
        )
    }

    fun showAddApp() {
        _state.value = _state.value.copy(
            destination = LaunchDestination.ADD_APP,
            pilotSurface = PilotSurface.NONE,
            error = null,
        )
    }

    fun createApp(name: String, packageName: String, optInUrl: String, groupUrl: String?) =
        createApp(name, packageName, optInUrl, groupUrl, "LAUNCH_CIRCLE")

    fun createApp(
        name: String,
        packageName: String,
        optInUrl: String,
        groupUrl: String?,
        groupMode: String,
    ) = createApp(name, packageName, optInUrl, groupUrl, groupMode, emptyList())

    fun createApp(
        name: String,
        packageName: String,
        optInUrl: String,
        groupUrl: String?,
        groupMode: String,
        coreWorkflowSteps: List<String>,
    ) = createApp(
        name, packageName, optInUrl, groupUrl, groupMode, coreWorkflowSteps, "",
    )

    fun createApp(
        name: String,
        packageName: String,
        optInUrl: String,
        groupUrl: String?,
        groupMode: String,
        coreWorkflowSteps: List<String>,
        playDeveloperAccountId: String,
        circleId: String? = null,
    ) = runTask {
        val request = CreateAppRequest(
            name = name,
            package_name = packageName,
            opt_in_url = optInUrl,
            google_group_url = groupUrl?.ifBlank { null },
            google_group_mode = groupMode,
            core_workflow_steps = coreWorkflowSteps,
            play_developer_account_id = playDeveloperAccountId,
            circle_id = circleId,
        )
        val app = try {
            repository.createApp(request)
        } catch (error: HttpException) {
            if (error.code() != 402) throw error
            pendingAppRequest = request
            val payment = repository.createAdditionalAppCheckout(playDeveloperAccountId)
            return@runTask _state.value.copy(
                pilotSurface = PilotSurface.ADDITIONAL_APP_PAYMENT,
                pendingPayment = payment,
                googlePlayPrice = null,
                googlePlayListPrice = null,
            )
        }
        pendingAppRequest = null
        val apps = repository.launches()
        val dashboards = apps.associate { it.id to repository.dashboard(it.id) }
        _state.value.copy(
            selectedApp = app,
            launches = apps,
            dashboards = dashboards,
            pendingPayment = null,
            pilotSurface = PilotSurface.GROUP_SETUP,
        )
    }

    fun launchAdditionalAppPurchase(activity: Activity) = runTask {
        val purchase = checkNotNull(_state.value.pendingPayment)
        activePurchaseId = purchase.id
        activePurchaseType = "ADDITIONAL_APP"
        billingGateway(activity).launchPurchase(activity, purchase.product_id, purchase.id) { price ->
            _state.value = _state.value.copy(googlePlayPrice = price)
        }
        _state.value
    }

    fun loadGooglePlayPrice(activity: Activity, productId: String, listProductId: String? = null) {
        _state.value = _state.value.copy(googlePlayPrice = null, googlePlayListPrice = null)
        val gateway = billingGateway(activity)
        gateway.queryPrice(productId) { price ->
            _state.value = _state.value.copy(googlePlayPrice = price, error = null)
        }
        if (listProductId != null) gateway.queryPrice(listProductId) { price ->
            _state.value = _state.value.copy(googlePlayListPrice = price, error = null)
        }
    }

    fun checkAdditionalAppPayment() = runTask {
        val payment = checkNotNull(_state.value.pendingPayment)
        refreshAdditionalAppPayment(payment.id)
        _state.value
    }

    fun recoverAdditionalAppPurchase(activity: Activity) {
        val payment = _state.value.pendingPayment ?: return
        activePurchaseId = payment.id
        activePurchaseType = "ADDITIONAL_APP"
        _state.value = _state.value.copy(loading = true, error = null)
        billingGateway(activity).queryOwnedPurchase(payment.product_id) { token ->
            viewModelScope.launch {
                runCatching {
                    if (token != null) {
                        repository.verifyGooglePlayPurchase(payment.id, "ADDITIONAL_APP", token)
                    }
                    // A newly verified purchase can take a short time to become
                    // visible to the status endpoint. Retry only the read.
                    var refreshed: AdditionalAppCheckout? = null
                    repeat(3) { attempt ->
                        refreshed = repository.additionalAppCheckout(payment.id)
                        if (refreshed?.status in setOf("PAID", "CONSUMED")) return@repeat
                        if (attempt < 2) delay(700)
                    }
                    refreshAdditionalAppPayment(payment.id)
                    _state.value
                }.onSuccess { state ->
                    _state.value = state.copy(loading = false)
                }.onFailure { error ->
                    _state.value = _state.value.copy(
                        loading = false,
                        error = errorMessage(error),
                    )
                }
            }
        }
    }

    private suspend fun refreshAdditionalAppPayment(purchaseId: String) {
        val refreshed = repository.additionalAppCheckout(purchaseId)
        val oldPayment = _state.value.pendingPayment
        val request = pendingAppRequest.takeIf { oldPayment?.id == purchaseId }
        if (refreshed.status in setOf("PAID", "CONSUMED") && request != null) {
            val app = repository.createApp(request)
            pendingAppRequest = null
            val apps = repository.launches()
            val dashboards = apps.associate { it.id to repository.dashboard(it.id) }
            _state.value = _state.value.copy(
                selectedApp = app,
                launches = apps,
                dashboards = dashboards,
                pendingPayment = null,
                pilotSurface = PilotSurface.GROUP_SETUP,
                error = null,
            )
        } else {
            _state.value = _state.value.copy(pendingPayment = refreshed, error = null)
        }
    }

    fun closeAdditionalAppPayment() {
        pendingAppRequest = null
        _state.value = _state.value.copy(
            pendingPayment = null,
            pilotSurface = PilotSurface.NONE,
            googlePlayPrice = null,
            googlePlayListPrice = null,
            error = null,
        )
    }

    fun startManagedCheckout(appId: String) = runTask {
        val payment = repository.createManagedCheckout(appId)
        _state.value.copy(
            pilotSurface = PilotSurface.MANAGED_PAYMENT,
            pendingManagedPayment = payment,
            googlePlayPrice = null,
            googlePlayListPrice = null,
        )
    }

    fun launchManagedPurchase(activity: Activity) = runTask {
        val purchase = checkNotNull(_state.value.pendingManagedPayment)
        activePurchaseId = purchase.id
        activePurchaseType = "MANAGED_LAUNCH"
        billingGateway(activity).launchPurchase(activity, purchase.product_id, purchase.id) { price ->
            _state.value = _state.value.copy(googlePlayPrice = price)
        }
        _state.value
    }

    private fun billingGateway(activity: Activity): PlayBillingGateway {
        playBillingGateway?.let { return it }
        return PlayBillingGateway(
            activity.applicationContext,
            onPurchaseToken = { token ->
                val purchaseId = activePurchaseId
                val purchaseType = activePurchaseType
                if (purchaseId != null && purchaseType != null) {
                    viewModelScope.launch {
                        runCatching {
                            repository.verifyGooglePlayPurchase(purchaseId, purchaseType, token)
                            if (purchaseType == "ADDITIONAL_APP") refreshAdditionalAppPayment(purchaseId)
                            else refreshManagedPayment(purchaseId)
                        }.onFailure { error ->
                            _state.value = _state.value.copy(error = errorMessage(error))
                        }
                    }
                }
            },
            onError = { message -> _state.value = _state.value.copy(error = message) },
        ).also { playBillingGateway = it }
    }

    override fun onCleared() {
        playBillingGateway?.close()
        super.onCleared()
    }

    fun checkManagedPayment() = runTask {
        val payment = checkNotNull(_state.value.pendingManagedPayment)
        refreshManagedPayment(payment.id)
        _state.value
    }

    private suspend fun refreshManagedPayment(checkoutId: String) {
        val refreshed = repository.managedCheckout(checkoutId)
        val apps = if (refreshed.status == "PAID") repository.launches() else _state.value.launches
        val dashboards = if (refreshed.status == "PAID") {
            apps.associate { it.id to repository.dashboard(it.id) }
        } else {
            _state.value.dashboards
        }
        _state.value = _state.value.copy(
            pendingManagedPayment = refreshed,
            launches = apps,
            dashboards = dashboards,
            selectedApp = if (refreshed.status == "PAID") {
                apps.firstOrNull { it.id == refreshed.app_id } ?: _state.value.selectedApp
            } else {
                _state.value.selectedApp
            },
            error = null,
        )
    }

    fun closeManagedPayment() {
        _state.value = _state.value.copy(
            pendingManagedPayment = null,
            pilotSurface = PilotSurface.NONE,
            googlePlayPrice = null,
            googlePlayListPrice = null,
            error = null,
        )
    }

    fun showGoogleGroupSetup() {
        _state.value = _state.value.copy(pilotSurface = PilotSurface.GROUP_SETUP, error = null)
    }

    fun confirmGoogleGroup() = runTask {
        val app = checkNotNull(_state.value.selectedApp)
        val updated = repository.confirmGoogleGroup(app.id)
        _state.value.copy(
            selectedApp = updated,
            launches = _state.value.launches.map { if (it.id == updated.id) updated else it },
            pilotSurface = PilotSurface.NONE,
            destination = LaunchDestination.DASHBOARD,
            dashboards = _state.value.dashboards + (updated.id to repository.dashboard(updated.id)),
        )
    }

    fun skipGroupSetup() {
        _state.value = _state.value.copy(
            pilotSurface = PilotSurface.NONE,
            destination = LaunchDestination.DASHBOARD,
        )
    }

    fun showDashboard(app: LaunchApp) = runTask {
        _state.value.copy(
            destination = LaunchDestination.DASHBOARD,
            pilotSurface = PilotSurface.NONE,
            selectedApp = app,
            dashboards = _state.value.dashboards + (app.id to repository.dashboard(app.id)),
        )
    }

    fun showToday() = runTask {
        _state.value.copy(
            destination = LaunchDestination.TODAY_TESTS,
            pilotSurface = PilotSurface.NONE,
            todayAssignments = repository.todaysAssignments(),
        )
    }

    fun showAssignment(assignment: TestAssignment) {
        _state.value = _state.value.copy(
            destination = LaunchDestination.ASSIGNMENT,
            selectedAssignment = assignment,
            error = null,
        )
    }

    fun completeAssignment() = runTask {
        val assignment = checkNotNull(_state.value.selectedAssignment)
        val completed = repository.completeAssignment(assignment.id)
        _state.value.copy(
            destination = LaunchDestination.TODAY_TESTS,
            selectedAssignment = null,
            todayAssignments = _state.value.todayAssignments.map {
                if (it.id == completed.id) completed else it
            },
        )
    }

    fun showMission(mission: TestMission) {
        _state.value = _state.value.copy(
            destination = LaunchDestination.MISSION,
            selectedMission = mission,
            error = null,
        )
    }

    fun startMission() = withMission { mission ->
        repository.startMission(mission.id)
        _state.value
    }

    fun confirmOptIn() = withMission { mission ->
        repository.optIn(mission.assignment_id)
        _state.value.copy(selectedMission = mission.copy(assignment_status = "OPTED_IN"))
    }

    fun confirmInstalled() = withMission { mission ->
        repository.installed(mission.assignment_id)
        _state.value.copy(selectedMission = mission.copy(assignment_status = "ACTIVE"))
    }

    fun submitFeedback(
        launchOk: Boolean,
        coreFeatureOk: String,
        issue: String?,
        suggestion: String?,
    ) = withMission { mission ->
        repository.completeMission(mission.id)
        repository.submitFeedback(
            mission.id,
            FeedbackRequest(
                launch_ok = launchOk,
                core_feature_ok = coreFeatureOk,
                rating = null,
                issue_text = issue?.ifBlank { null },
                suggestion_text = suggestion?.ifBlank { null },
            ),
        )
        _state.value.copy(
            destination = LaunchDestination.TODAY_TESTS,
            selectedMission = null,
            today = repository.todaysMissions(),
        )
    }

    fun submitFeedback(
        completionResult: String,
        issue: String?,
        suggestion: String?,
        timeSpentMinutes: Int? = null,
    ) = withMission { mission ->
        val coreFeatureOk = when (completionResult) {
            "COMPLETED" -> "YES"
            "COMPLETED_WITH_DIFFICULTY" -> "PARTLY"
            else -> "NO"
        }
        repository.completeMission(mission.id)
        repository.submitFeedback(
            mission.id,
            FeedbackRequest(
                launch_ok = true,
                core_feature_ok = coreFeatureOk,
                rating = null,
                issue_text = issue?.ifBlank { null },
                suggestion_text = suggestion?.ifBlank { null },
                completion_result = completionResult,
                time_spent_minutes = timeSpentMinutes,
            ),
        )
        _state.value.copy(
            destination = LaunchDestination.TODAY_TESTS,
            selectedMission = null,
            today = repository.todaysMissions(),
        )
    }

    fun recordCoordinationTime(minutes: Int, category: String = "COORDINATION") = runTask {
        val app = checkNotNull(_state.value.selectedApp)
        repository.recordCoordinationTime(app.id, minutes, category)
        _state.value.copy(
            dashboards = _state.value.dashboards + (app.id to repository.dashboard(app.id)),
        )
    }

    fun recordManagedOfferViewed(appId: String, trigger: String) {
        viewModelScope.launch {
            runCatching { repository.recordManagedOfferViewed(appId, trigger) }
        }
    }

    fun matchTesters() = runTask {
        val app = checkNotNull(_state.value.selectedApp)
        val result = repository.matchTesters(app.id)
        _state.value.copy(
            destination = LaunchDestination.DASHBOARD,
            matchingResult = result,
            dashboards = _state.value.dashboards + (app.id to repository.dashboard(app.id)),
        )
    }

    fun showTesters() = runTask {
        val app = checkNotNull(_state.value.selectedApp)
        _state.value.copy(
            destination = LaunchDestination.TESTERS,
            testers = repository.testers(app.id),
            circle = repository.circle(app.id),
        )
    }

    fun showCircle() {
        val joinedCircle = _state.value.circle
        if (joinedCircle != null && _state.value.selectedApp == null) {
            _state.value = _state.value.copy(
                destination = LaunchDestination.TESTERS,
                pilotSurface = PilotSurface.NONE,
                testers = emptyList(),
                error = null,
            )
            return
        }
        val app = _state.value.selectedApp ?: _state.value.launches.firstOrNull()
        if (app == null) {
            _state.value = _state.value.copy(destination = LaunchDestination.MY_LAUNCHES)
            return
        }
        _state.value = _state.value.copy(selectedApp = app)
        showTesters()
    }

    fun showFeedback() = runTask {
        val app = checkNotNull(_state.value.selectedApp)
        _state.value.copy(
            destination = LaunchDestination.FEEDBACK,
            feedback = repository.feedback(app.id),
        )
    }

    fun showInvite() {
        val app = _state.value.selectedApp ?: _state.value.launches.firstOrNull()
        _state.value = _state.value.copy(pilotSurface = PilotSurface.INVITE, error = null)
        if (_state.value.invite == null) {
            runTask {
                val invite = app?.let { repository.createInvite(it.id) }
                    ?: repository.createCircleInvite()
                _state.value.copy(
                    pilotSurface = PilotSurface.INVITE,
                    invite = invite,
                )
            }
        }
    }

    fun refreshInvite() = runTask {
        val app = _state.value.selectedApp ?: _state.value.launches.firstOrNull()
        val invite = app?.let { repository.createInvite(it.id) }
            ?: repository.createCircleInvite()
        _state.value.copy(
            pilotSurface = PilotSurface.INVITE,
            invite = invite,
        )
    }

    fun createInvite() = showInvite()

    fun showJoin() {
        _state.value = _state.value.copy(pilotSurface = PilotSurface.JOIN, error = null)
    }

    fun acceptInvite(code: String) {
        if (!InviteCodeValidator.isValid(code)) {
            _state.value = _state.value.copy(error = "Enter a code like LC-8H4K2")
            return
        }
        runTask {
            val invite = repository.acceptInvite(InviteCodeValidator.normalize(code))
            val availableCircles = repository.circles()
            _state.value.copy(
                availableCircles = availableCircles,
                invite = invite,
                circle = invite.circle_id?.let { repository.circle(it) },
                pilotSurface = PilotSurface.JOIN_SUCCESS,
            )
        }
    }

    fun closePilotSurface() {
        _state.value = _state.value.copy(pilotSurface = PilotSurface.NONE, error = null)
    }

    fun back() {
        if (_state.value.pilotSurface != PilotSurface.NONE) {
            closePilotSurface()
            return
        }
        val target = when (_state.value.destination) {
            LaunchDestination.ADD_APP,
            LaunchDestination.DASHBOARD,
            LaunchDestination.TODAY_TESTS,
            LaunchDestination.ACCOUNT -> LaunchDestination.MY_LAUNCHES
            LaunchDestination.ASSIGNMENT -> LaunchDestination.TODAY_TESTS
            LaunchDestination.MISSION -> LaunchDestination.TODAY_TESTS
            LaunchDestination.TESTERS,
            LaunchDestination.FEEDBACK -> LaunchDestination.DASHBOARD
            LaunchDestination.MY_LAUNCHES -> LaunchDestination.MY_LAUNCHES
        }
        _state.value = _state.value.copy(destination = target, error = null)
    }

    private fun runTask(block: suspend () -> LaunchUiState) {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching { block() }
                .onSuccess { _state.value = it.copy(loading = false) }
                .onFailure {
                    val message = when {
                        it is HttpException && it.code() == 402 ->
                            "This Developer Account already used its free app. Additional apps cost \$1."
                        it is HttpException && it.code() == 503 ->
                            "Secure checkout is unavailable right now. No payment has been taken; try again later."
                        else -> errorMessage(it)
                    }
                    _state.value = _state.value.copy(loading = false, error = message)
                }
        }
    }

    private fun errorMessage(error: Throwable): String {
        val serverDetail = (error as? HttpException)?.response()?.errorBody()?.use { body ->
            runCatching { org.json.JSONObject(body.string()).optString("detail") }
                .getOrNull()
                ?.takeIf { it.isNotBlank() && it != "null" }
        }
        if (serverDetail != null) return serverDetail
        return error.message ?: "Something went wrong. Try again."
    }

    private fun withMission(block: suspend (TestMission) -> LaunchUiState) {
        runTask { block(checkNotNull(_state.value.selectedMission)) }
    }
}
