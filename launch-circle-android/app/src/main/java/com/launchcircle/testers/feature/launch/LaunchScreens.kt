package com.launchcircle.testers.feature.launch

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchDashboard
import com.launchcircle.testers.core.model.MissionFeedback
import com.launchcircle.testers.core.model.TestMission
import com.launchcircle.testers.core.model.TesterAssignment
import com.launchcircle.testers.core.model.UserProfile

@Composable
fun LegacyLaunchWorkspace(
    profile: UserProfile,
    viewModel: LaunchViewModel,
    onLogout: () -> Unit,
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(viewModel, profile.id) {
        viewModel.loadLaunches(profile.id)
    }
    Column(Modifier.fillMaxSize()) {
        if (state.destination != LaunchDestination.MY_LAUNCHES) {
            OutlinedButton(
                onClick = viewModel::back,
                modifier = Modifier.padding(start = 16.dp, top = 8.dp),
            ) { Text("Back") }
        }
        state.error?.let {
            Text(
                it,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
        when {
            state.loading && state.destination == LaunchDestination.MY_LAUNCHES && state.launches.isEmpty() -> CircularProgressIndicator(Modifier.padding(24.dp))
            state.destination == LaunchDestination.MY_LAUNCHES -> MyLaunchesScreen(
                profile = profile,
                launches = state.launches,
                dashboards = state.dashboards,
                onAdd = viewModel::showAddApp,
                onLaunch = viewModel::showDashboard,
                onToday = viewModel::showToday,
                onLogout = onLogout,
            )
            state.destination == LaunchDestination.ADD_APP -> AddAppScreen(
                viewModel::createApp,
                viewModel::setDraftIcon,
            )
            state.destination == LaunchDestination.DASHBOARD -> {
                val app = state.selectedApp
                val dashboard = app?.let { state.dashboards[it.id] }
                if (app != null && dashboard != null) {
                    DashboardScreen(
                        app,
                        dashboard,
                        state.invite,
                        viewModel::matchTesters,
                        viewModel::showTesters,
                        viewModel::createInvite,
                        viewModel::showFeedback,
                    )
                }
            }
            state.destination == LaunchDestination.TODAY_TESTS ->
                TodayTestsScreen(state.today, viewModel::showMission)
            state.destination == LaunchDestination.MISSION ->
                state.selectedMission?.let {
                    MissionFeedbackScreen(
                        it,
                        viewModel::confirmOptIn,
                        viewModel::confirmInstalled,
                        viewModel::submitFeedback,
                    )
                }
            state.destination == LaunchDestination.TESTERS ->
                TesterStatusScreen(state.testers)
            state.destination == LaunchDestination.FEEDBACK ->
                FeedbackListScreen(state.feedback)
        }
    }
}

@Composable
private fun MyLaunchesScreen(
    profile: UserProfile,
    launches: List<LaunchApp>,
    dashboards: Map<String, LaunchDashboard>,
    onAdd: () -> Unit,
    onLaunch: (LaunchApp) -> Unit,
    onToday: () -> Unit,
    onLogout: () -> Unit,
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text("My Launches", style = MaterialTheme.typography.headlineMedium)
            Text("Welcome, " + (profile.display_name ?: "developer"))
            Row(
                Modifier.fillMaxWidth().padding(top = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Button(onClick = onAdd) { Text("Add App") }
                OutlinedButton(onClick = onToday) { Text("Today's Tests") }
            }
        }
        if (launches.isEmpty()) {
            item {
                Text("No launches yet. Add an app to begin gathering testers.")
            }
        }
        items(launches, key = { it.id }) { app ->
            val dashboard = dashboards[app.id]
            Card(onClick = { onLaunch(app) }, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text(app.name, style = MaterialTheme.typography.titleLarge)
                    Text(
                        (dashboard?.assigned_testers ?: 0).toString() +
                            " / " + app.tester_target + " testers"
                    )
                    if ((dashboard?.day ?: 0) > 0) {
                        Text("Day " + dashboard?.day + " / 14")
                    }
                    Text(prettyStatus(dashboard?.status ?: app.status))
                }
            }
        }
        item {
            OutlinedButton(onClick = onLogout) { Text("Sign out") }
        }
    }
}

@Composable
private fun AddAppScreen(
    onCreate: (String, String, String, String?, String, List<String>, String, String?, Boolean) -> Unit,
    onDraftIcon: (String?) -> Unit,
) {
    var name by remember { mutableStateOf("") }
    var packageName by remember { mutableStateOf("") }
    var optInUrl by remember { mutableStateOf("") }
    var draftIcon by remember { mutableStateOf<String?>(null) }
    var ownershipAuthorized by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { onDraftIcon(null) }
    val canCreate = name.isNotBlank() && draftIcon != null &&
        packageName.contains(".") &&
        optInUrl.startsWith("http") && ownershipAuthorized

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text("Add App", style = MaterialTheme.typography.headlineMedium)
        IconUpload(name.ifBlank { "App" }, draftIcon?.let { "data:image/png;base64,$it" }) {
            draftIcon = it
            onDraftIcon(it)
        }
        Text("Required: PNG or JPEG, up to 1 MB.")
        OutlinedTextField(
            name, { name = it }, label = { Text("App name") },
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            packageName, { packageName = it }, label = { Text("Package name") },
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            optInUrl, { optInUrl = it },
            label = { Text("Google Play closed-testing opt-in URL") },
            modifier = Modifier.fillMaxWidth(),
        )
        Text(
            lcText(
                "Launch Circle uses one shared tester group. After creating this app, add the group email to its Play closed-test track. Testers join the group once, then opt in to each app separately.",
                "Launch Circle 统一使用一个测试群组。添加此 App 后，请在它自己的 Play 封闭测试轨道添加群组邮箱。测试者只需加入群组一次，但每个 App 都要单独加入 Play 测试。",
            ),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
            Checkbox(checked = ownershipAuthorized, onCheckedChange = { ownershipAuthorized = it })
            Text("I own this app or am authorized to submit it for testing. Publisher identity is self-reported and may not be independently verified.")
        }
        Button(
            onClick = {
                onCreate(
                    name,
                    packageName,
                    optInUrl,
                    null,
                    "LAUNCH_CIRCLE",
                    listOf("Open the app and complete its main task.", "Check that the task result is clear and correct."),
                    "",
                    null,
                    ownershipAuthorized,
                )
            },
            enabled = canCreate,
        ) { Text("Create Launch") }
    }
}

@Composable
private fun DashboardScreen(
    app: LaunchApp,
    dashboard: LaunchDashboard,
    invite: com.launchcircle.testers.core.model.LaunchInvite?,
    onMatch: () -> Unit,
    onTesters: () -> Unit,
    onInvite: () -> Unit,
    onFeedback: () -> Unit,
) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(app.name, style = MaterialTheme.typography.headlineMedium)
        Text(prettyStatus(dashboard.status), color = MaterialTheme.colorScheme.primary)
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp)) {
                Text("Production Readiness")
                Text(
                    dashboard.production_readiness.toString() + "%",
                    style = MaterialTheme.typography.displayMedium,
                )
                Text(dashboard.approval_disclaimer, style = MaterialTheme.typography.bodySmall)
            }
        }
        Text("TESTERS", style = MaterialTheme.typography.titleMedium)
        Text("${dashboard.active_testers} active / ${dashboard.tester_target} target")
        Text("${dashboard.assigned_testers} assigned")
        Text("${dashboard.google_minimum} minimum")
        Text("${dashboard.continuous_qualifying_testers} continuous qualifying")
        Text("${dashboard.at_risk_testers} at risk · ${dashboard.replacement_testers} replacement")
        if (dashboard.testers_needed_for_minimum > 0) {
            Text(
                "Need ${dashboard.testers_needed_for_minimum} more to reach Google’s minimum",
                color = MaterialTheme.colorScheme.primary,
            )
        }
        HorizontalDivider()
        Text("TESTING", style = MaterialTheme.typography.titleMedium)
        Text("Day ${dashboard.day} / ${dashboard.total_days}")
        Text("${dashboard.days_remaining} days remaining")
        Text("Estimated ready: ${dashboard.estimated_ready_date}")
        Text(
            "Mission progress: ${dashboard.missions_completed} / " +
                "${dashboard.missions_total_available} available",
        )
        HorizontalDivider()
        Text("CIRCLE HEALTH", style = MaterialTheme.typography.titleMedium)
        Text(
            prettyStatus(dashboard.circle_health),
            color = if (dashboard.circle_health == "GOOD") {
                MaterialTheme.colorScheme.primary
            } else {
                MaterialTheme.colorScheme.error
            },
        )
        Text("TODAY", style = MaterialTheme.typography.titleMedium)
        Text("${dashboard.today_tasks} tests remaining")
        Text("Feedback received: ${dashboard.feedback_count}")
        Button(onClick = onMatch, modifier = Modifier.fillMaxWidth()) {
            Text("Match Eligible Testers")
        }
        Button(onClick = onTesters, modifier = Modifier.fillMaxWidth()) {
            Text("View Testers")
        }
        Button(onClick = onInvite, modifier = Modifier.fillMaxWidth()) {
            Text(lcText("Share this app’s test invitation", "分享此 App 的测试邀请"))
        }
        OutlinedButton(onClick = onFeedback, modifier = Modifier.fillMaxWidth()) {
            Text("View Feedback")
        }
    }
}

@Composable
private fun TodayTestsScreen(
    missions: List<TestMission>,
    onMission: (TestMission) -> Unit,
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { Text("Today's Tests", style = MaterialTheme.typography.headlineMedium) }
        if (missions.isEmpty()) {
            item { Text("You're caught up. New meaningful missions appear on scheduled days.") }
        }
        items(missions, key = { it.id }) { mission ->
            Card(onClick = { onMission(mission) }, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text(mission.app_name, style = MaterialTheme.typography.titleLarge)
                    Text(prettyMission(mission.mission_type))
                    Text("~" + mission.estimated_minutes + " min")
                }
            }
        }
    }
}

@Composable
private fun MissionFeedbackScreen(
    mission: TestMission,
    onOptIn: () -> Unit,
    onInstalled: () -> Unit,
    onSubmit: (Boolean, String, String?, String?) -> Unit,
) {
    val initialStep = when (mission.assignment_status) {
        "ACTIVE", "COMPLETED" -> 3
        "OPTED_IN", "INSTALLED" -> 2
        else -> 0
    }
    var step by rememberSaveable(mission.id) { mutableIntStateOf(initialStep) }
    var launchOk by rememberSaveable(mission.id) { mutableStateOf<Boolean?>(null) }
    var featureOk by rememberSaveable(mission.id) { mutableStateOf<String?>(null) }
    var issue by rememberSaveable(mission.id) { mutableStateOf("") }
    var suggestion by rememberSaveable(mission.id) { mutableStateOf("") }
    val uriHandler = LocalUriHandler.current

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(mission.app_name, style = MaterialTheme.typography.headlineMedium)
        Text(prettyMission(mission.mission_type), style = MaterialTheme.typography.titleLarge)
        Text("About " + mission.estimated_minutes + " minutes")
        if (step == 0) {
            Button(
                onClick = {
                    uriHandler.openUri(mission.opt_in_url)
                    step = 1
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Open Play Testing Link") }
        }
        if (step == 1) {
            Button(
                onClick = {
                    onOptIn()
                    step = 2
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("I've Opted In") }
        }
        if (step == 2) {
            Button(
                onClick = {
                    onInstalled()
                    step = 3
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Installed") }
        }
        if (step == 3) {
            Text("Complete the mission: " + prettyMission(mission.mission_type))
            Button(onClick = { step = 4 }, modifier = Modifier.fillMaxWidth()) {
                Text("Start Mission")
            }
        }
        if (step >= 4) {
            Text("Did the app open successfully?")
            ChoiceRow(
                listOf("Yes", "No"),
                launchOk?.let { if (it) "Yes" else "No" },
            ) { launchOk = it == "Yes" }
            Text("Did the main feature work?")
            ChoiceRow(listOf("Yes", "Partly", "No"), featureOk?.lowercase()?.replaceFirstChar {
                it.uppercase()
            }) { featureOk = it.uppercase() }
            OutlinedTextField(
                issue, { issue = it }, label = { Text("Any issue? (optional)") },
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                suggestion, { suggestion = it },
                label = { Text("Any suggestion? (optional)") },
                modifier = Modifier.fillMaxWidth(),
            )
            Button(
                onClick = {
                    onSubmit(
                        checkNotNull(launchOk),
                        checkNotNull(featureOk),
                        issue,
                        suggestion,
                    )
                },
                enabled = launchOk != null && featureOk != null,
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Submit Feedback") }
        }
    }
}

@Composable
private fun ChoiceRow(
    choices: List<String>,
    selected: String?,
    onSelect: (String) -> Unit,
) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        choices.forEach { choice ->
            if (selected == choice) {
                Button(onClick = { onSelect(choice) }) { Text(choice) }
            } else {
                OutlinedButton(onClick = { onSelect(choice) }) { Text(choice) }
            }
        }
    }
}

@Composable
private fun TesterStatusScreen(testers: List<TesterAssignment>) {
    val assigned = testers.count { it.status != "DROPPED" }
    val active = testers.count {
        it.status in setOf("ACTIVE", "COMPLETED") &&
            it.health_status in setOf("NEW", "GOOD")
    }
    val new = testers.count { it.health_status == "NEW" }
    val atRisk = testers.count { it.health_status in setOf("AT_RISK", "INACTIVE") }
    val replacements = testers.count { it.is_replacement && it.status != "DROPPED" }
    val dropped = testers.count { it.status == "DROPPED" || it.health_status == "DROPPED" }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item {
            Text("Tester Status", style = MaterialTheme.typography.headlineMedium)
            Text("$assigned assigned · $active active")
            Text("$new new · $atRisk at risk")
            Text("$replacements replacement · $dropped dropped")
            Spacer(Modifier.height(8.dp))
        }
        items(testers, key = { it.id }) { tester ->
            val healthLabel = when {
                tester.status == "DROPPED" || tester.health_status == "DROPPED" -> "Dropped"
                tester.health_status == "INACTIVE" -> "At Risk · Inactive"
                tester.health_status == "AT_RISK" -> "At Risk"
                tester.is_replacement -> "Replacement · ${prettyStatus(tester.health_status)}"
                tester.health_status == "NEW" -> "New"
                else -> "Active · Good"
            }
            val risky = tester.health_status in setOf("AT_RISK", "INACTIVE", "DROPPED") ||
                tester.status == "DROPPED"
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text(tester.tester_label, style = MaterialTheme.typography.titleMedium)
                    Text(
                        healthLabel,
                        color = if (risky) {
                            MaterialTheme.colorScheme.error
                        } else {
                            MaterialTheme.colorScheme.primary
                        },
                    )
                    Text("Day ${tester.testing_day}")
                    Text("${tester.completed_missions} / ${tester.total_missions} missions")
                    if (tester.replacement_for_id != null) {
                        Text("Fresh replacement timeline", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }
}

@Composable
private fun FeedbackListScreen(rows: List<MissionFeedback>) {
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item { Text("Feedback", style = MaterialTheme.typography.headlineMedium) }
        if (rows.isEmpty()) item { Text("No feedback has been submitted yet.") }
        items(rows, key = { it.id }) { row ->
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text(row.tester_label + " · " + prettyMission(row.mission_type))
                    Text("Opened: " + when (row.launch_ok) {
                        true -> "Yes"
                        false -> "No"
                        null -> "Not answered"
                    })
                    Text("Core feature: " + (row.core_feature_ok ?: "Not answered"))
                    row.issue_text?.let { Text("Issue: " + it) }
                    row.suggestion_text?.let { Text("Suggestion: " + it) }
                }
            }
        }
    }
}

private fun prettyMission(value: String): String =
    value.lowercase().split("_").joinToString(" ") { word ->
        word.replaceFirstChar { it.uppercase() }
    }

private fun prettyStatus(value: String): String =
    value.lowercase().split("_").joinToString(" ") { word ->
        word.replaceFirstChar { it.uppercase() }
    }
