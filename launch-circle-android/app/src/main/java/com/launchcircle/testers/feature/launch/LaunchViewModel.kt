package com.launchcircle.testers.feature.launch

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.launchcircle.testers.core.launch.InviteCodeValidator
import com.launchcircle.testers.core.launch.LaunchRepository
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
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class LaunchDestination {
    MY_LAUNCHES, ADD_APP, DASHBOARD, TODAY_TESTS, MISSION, TESTERS, FEEDBACK, ACCOUNT
}

enum class PilotSurface { NONE, INVITE, JOIN, JOIN_SUCCESS, GROUP_SETUP }

data class LaunchUiState(
    val destination: LaunchDestination = LaunchDestination.MY_LAUNCHES,
    val pilotSurface: PilotSurface = PilotSurface.NONE,
    val pilotConfig: PilotConfig = PilotConfig(),
    val launches: List<LaunchApp> = emptyList(),
    val dashboards: Map<String, LaunchDashboard> = emptyMap(),
    val selectedApp: LaunchApp? = null,
    val selectedMission: TestMission? = null,
    val testers: List<TesterAssignment> = emptyList(),
    val feedback: List<MissionFeedback> = emptyList(),
    val today: List<TestMission> = emptyList(),
    val invite: LaunchInvite? = null,
    val matchingResult: MatchingResult? = null,
    val loading: Boolean = true,
    val error: String? = null,
)

class LaunchViewModel(private val repository: LaunchRepository) : ViewModel() {
    private var loadedUserId: String? = null
    private val _state = MutableStateFlow(LaunchUiState())
    val state: StateFlow<LaunchUiState> = _state.asStateFlow()

    fun loadLaunches(userId: String) {
        if (loadedUserId == userId) return
        loadedUserId = userId
        _state.value = LaunchUiState()
        runTask {
            val config = runCatching { repository.pilotConfig() }.getOrDefault(PilotConfig())
            val apps = repository.launches()
            val dashboards = apps.associate { it.id to repository.dashboard(it.id) }
            _state.value.copy(
                destination = LaunchDestination.MY_LAUNCHES,
                pilotConfig = config,
                launches = apps,
                dashboards = dashboards,
            )
        }
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
    ) = runTask {
        val app = repository.createApp(
            CreateAppRequest(
                name,
                packageName,
                optInUrl,
                groupUrl?.ifBlank { null },
                groupMode,
            ),
        )
        val apps = repository.launches()
        val dashboards = apps.associate { it.id to repository.dashboard(it.id) }
        _state.value.copy(
            selectedApp = app,
            launches = apps,
            dashboards = dashboards,
            pilotSurface = PilotSurface.GROUP_SETUP,
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
            today = repository.todaysMissions(),
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
        )
    }

    fun showFeedback() = runTask {
        val app = checkNotNull(_state.value.selectedApp)
        _state.value.copy(
            destination = LaunchDestination.FEEDBACK,
            feedback = repository.feedback(app.id),
        )
    }

    fun showInvite() {
        _state.value = _state.value.copy(pilotSurface = PilotSurface.INVITE, error = null)
        if (_state.value.invite == null) {
            runTask {
                _state.value.copy(
                    pilotSurface = PilotSurface.INVITE,
                    invite = repository.createInvite(),
                )
            }
        }
    }

    fun refreshInvite() = runTask {
        _state.value.copy(
            pilotSurface = PilotSurface.INVITE,
            invite = repository.createInvite(),
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
            _state.value.copy(
                invite = repository.acceptInvite(InviteCodeValidator.normalize(code)),
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
                    _state.value = _state.value.copy(
                        loading = false,
                        error = it.message ?: "Something went wrong. Try again.",
                    )
                }
        }
    }

    private fun withMission(block: suspend (TestMission) -> LaunchUiState) {
        runTask { block(checkNotNull(_state.value.selectedMission)) }
    }
}
