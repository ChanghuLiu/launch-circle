package com.launchcircle.testers.feature.launch

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchDashboard
import com.launchcircle.testers.core.model.LaunchInvite
import com.launchcircle.testers.core.model.MissionFeedback
import com.launchcircle.testers.core.model.PilotConfig
import com.launchcircle.testers.core.model.TestMission
import com.launchcircle.testers.core.model.TesterAssignment
import com.launchcircle.testers.core.model.UserProfile
import com.launchcircle.testers.feature.onboarding.AccountScreen

@Composable
fun LaunchWorkspace(
    profile: UserProfile,
    viewModel: LaunchViewModel,
    deletionInProgress: Boolean,
    deletionError: String?,
    onDeleteAccount: () -> Unit,
    onLogout: () -> Unit,
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(viewModel, profile.id) { viewModel.loadLaunches(profile.id) }
    Surface(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize()) {
            if (state.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
            if (state.pilotSurface == PilotSurface.NONE &&
                state.destination != LaunchDestination.MY_LAUNCHES
            ) {
                OutlinedButton(
                    onClick = viewModel::back,
                    modifier = Modifier.padding(start = 16.dp, top = 8.dp),
                ) { Text("Back") }
            }
            state.error?.let { ErrorBanner(it) }
            Box(Modifier.fillMaxSize()) {
                when (state.pilotSurface) {
                    PilotSurface.INVITE -> InviteScreen(
                        state.invite, state.loading, viewModel::refreshInvite,
                        viewModel::closePilotSurface,
                    )
                    PilotSurface.JOIN -> JoinScreen(
                        state.loading, viewModel::acceptInvite, viewModel::closePilotSurface,
                    )
                    PilotSurface.JOIN_SUCCESS -> JoinSuccess(
                        state.pilotConfig,
                        {
                            viewModel.closePilotSurface()
                            viewModel.showAddApp()
                        },
                        {
                            viewModel.closePilotSurface()
                            viewModel.showToday()
                        },
                    )
                    PilotSurface.GROUP_SETUP -> state.selectedApp?.let {
                        GroupSetup(
                            it, state.pilotConfig, state.loading,
                            viewModel::confirmGoogleGroup, viewModel::skipGroupSetup,
                        )
                    }
                    PilotSurface.NONE -> when (state.destination) {
                        LaunchDestination.MY_LAUNCHES -> Home(
                            profile, state.launches, state.dashboards,
                            viewModel::showAddApp, viewModel::showDashboard,
                            viewModel::showToday, viewModel::showInvite,
                            viewModel::showJoin, viewModel::showAccount, onLogout,
                        )
                        LaunchDestination.ADD_APP -> AddApp(
                            state.pilotConfig, viewModel::createApp,
                        )
                        LaunchDestination.DASHBOARD -> {
                            val selected = state.selectedApp
                            val dashboard = selected?.let { state.dashboards[it.id] }
                            if (selected != null && dashboard != null) {
                                Dashboard(
                                    selected, dashboard, state.loading,
                                    viewModel::showInvite, viewModel::matchTesters,
                                    viewModel::showTesters, viewModel::showFeedback,
                                    viewModel::showGoogleGroupSetup,
                                )
                            }
                        }
                        LaunchDestination.TODAY_TESTS -> Today(
                            state.today, state.pilotConfig, viewModel::showMission,
                        )
                        LaunchDestination.MISSION -> state.selectedMission?.let {
                            Mission(
                                it, viewModel::startMission, viewModel::confirmOptIn,
                                viewModel::confirmInstalled, viewModel::submitFeedback,
                            )
                        }
                        LaunchDestination.TESTERS -> Testers(state.testers)
                        LaunchDestination.FEEDBACK -> Feedback(state.feedback)
                        LaunchDestination.ACCOUNT -> AccountScreen(
                            deleting = deletionInProgress,
                            error = deletionError,
                            onBack = viewModel::back,
                            onDeleteAccount = onDeleteAccount,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun Home(
    profile: UserProfile,
    apps: List<LaunchApp>,
    dashboards: Map<String, LaunchDashboard>,
    onAdd: () -> Unit,
    onOpen: (LaunchApp) -> Unit,
    onToday: () -> Unit,
    onInvite: () -> Unit,
    onJoin: () -> Unit,
    onAccount: () -> Unit,
    onLogout: () -> Unit,
) {
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Spacer(Modifier.height(20.dp))
            Text("Launch Circle", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
            Text("12 Testers", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
            Text(
                "Find testers. Complete your 14-day closed test. Prepare for production.",
                modifier = Modifier.padding(top = 8.dp),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "Welcome, " + (profile.display_name ?: "developer"),
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
        item {
            Button(onClick = onAdd, modifier = Modifier.fillMaxWidth()) { Text("+ Add App") }
            Row(
                Modifier.fillMaxWidth().padding(top = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                OutlinedButton(onClick = onInvite, modifier = Modifier.weight(1f)) {
                    Text("Invite Developers")
                }
                OutlinedButton(onClick = onToday, modifier = Modifier.weight(1f)) {
                    Text("Today's Tests")
                }
            }
            OutlinedButton(onClick = onJoin, modifier = Modifier.fillMaxWidth()) {
                Text("I have an invite code")
            }
        }
        if (apps.isEmpty()) {
            item {
                EmptyCard(
                    "Your first launch starts here",
                    "Add an app, connect tester access, then invite developers or match available testers.",
                )
            }
        }
        items(apps, key = { it.id }) { app ->
            LaunchCard(app, dashboards[app.id]) { onOpen(app) }
        }
        item {
            OutlinedButton(onClick = onAccount, modifier = Modifier.fillMaxWidth()) {
                Text("Account / Settings")
            }
            OutlinedButton(onClick = onLogout, modifier = Modifier.fillMaxWidth()) { Text("Sign out") }
            Spacer(Modifier.height(20.dp))
        }
    }
}

@Composable
private fun LaunchCard(app: LaunchApp, dashboard: LaunchDashboard?, onOpen: () -> Unit) {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(app.name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                StatusChip(pretty(dashboard?.status ?: app.status))
            }
            val active = dashboard?.active_testers ?: 0
            val readiness = dashboard?.production_readiness ?: 0
            Text(active.toString() + " / 12 minimum", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text("Target: " + app.tester_target)
            Text("Day " + (dashboard?.day ?: 0) + " / 14")
            Text("Production readiness · " + readiness + "%")
            LinearProgressIndicator(progress = { readiness / 100f }, modifier = Modifier.fillMaxWidth())
            val needed = dashboard?.testers_needed_for_minimum ?: 0
            if (needed > 0) {
                Text("Need " + needed + " more to reach the minimum.", color = MaterialTheme.colorScheme.primary)
            }
            Button(onClick = onOpen, modifier = Modifier.fillMaxWidth()) { Text("Open Launch") }
        }
    }
}

@Composable
private fun AddApp(
    config: PilotConfig,
    onCreate: (String, String, String, String?, String) -> Unit,
) {
    var name by rememberSaveable { mutableStateOf("") }
    var packageName by rememberSaveable { mutableStateOf("") }
    var optIn by rememberSaveable { mutableStateOf("") }
    var mode by rememberSaveable { mutableStateOf("LAUNCH_CIRCLE") }
    var ownUrl by rememberSaveable { mutableStateOf("") }
    val context = LocalContext.current
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Add your app", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("A guided setup for your closed test.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Section("APP DETAILS")
        OutlinedTextField(name, { name = it }, label = { Text("App name") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(packageName, { packageName = it }, label = { Text("Package name") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(optIn, { optIn = it }, label = { Text("Closed-testing opt-in URL") }, modifier = Modifier.fillMaxWidth())
        Section("TESTER ACCESS")
        Option(mode == "LAUNCH_CIRCLE", "Launch Circle Google Group · Recommended", "Shared access for pilot testers.") {
            mode = "LAUNCH_CIRCLE"
        }
        if (mode == "LAUNCH_CIRCLE") {
            Highlight {
                Text("Group email")
                Text(config.google_group_email, fontWeight = FontWeight.SemiBold)
                OutlinedButton(onClick = { copy(context, config.google_group_email) }) {
                    Text("Copy Group Email")
                }
                Text(
                    "You still add this group to your Closed Testing track in Play Console.",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
        Option(mode == "OWN_GROUP", "Use my own Google Group", "Use an existing group URL.") {
            mode = "OWN_GROUP"
        }
        if (mode == "OWN_GROUP") {
            OutlinedTextField(ownUrl, { ownUrl = it }, label = { Text("Google Group URL") }, modifier = Modifier.fillMaxWidth())
        }
        Option(mode == "EMAIL_LIST", "Use email tester list", "Manage a fallback list in Play Console.") {
            mode = "EMAIL_LIST"
        }
        Button(
            onClick = { onCreate(name.trim(), packageName.trim(), optIn.trim(), ownUrl.ifBlank { null }, mode) },
            enabled = name.isNotBlank() && packageName.contains(".") && optIn.startsWith("http") &&
                (mode != "OWN_GROUP" || ownUrl.startsWith("http")),
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Create Launch") }
        Spacer(Modifier.height(20.dp))
    }
}

@Composable
private fun GroupSetup(
    app: LaunchApp,
    config: PilotConfig,
    loading: Boolean,
    onConfirm: () -> Unit,
    onLater: () -> Unit,
) {
    val context = LocalContext.current
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Connect tester access", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(app.name, color = MaterialTheme.colorScheme.primary)
        Highlight {
            Text("Launch Circle Google Group", fontWeight = FontWeight.SemiBold)
            Text(config.google_group_email)
            OutlinedButton(onClick = { copy(context, config.google_group_email) }) { Text("Copy Group Email") }
        }
        Text("Add the group in Play Console", style = MaterialTheme.typography.titleMedium)
        listOf(
            "1. Open Play Console",
            "2. Closed testing",
            "3. Manage testers",
            "4. Add Google Group",
            "5. Enter: " + config.google_group_email,
            "6. Save",
            "7. Return here and continue",
        ).forEach { Text(it) }
        Text(
            "This is your confirmation. Launch Circle does not modify or verify Play Console.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Button(onClick = onConfirm, enabled = !loading, modifier = Modifier.fillMaxWidth()) {
            Text("I've added the Google Group")
        }
        OutlinedButton(onClick = onLater, modifier = Modifier.fillMaxWidth()) { Text("I'll do this later") }
    }
}

@Composable
private fun Dashboard(
    app: LaunchApp,
    data: LaunchDashboard,
    loading: Boolean,
    onInvite: () -> Unit,
    onMatch: () -> Unit,
    onTesters: () -> Unit,
    onFeedback: () -> Unit,
    onGroupSetup: () -> Unit,
) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(app.name, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        StatusChip(pretty(data.status))
        Metric("Production readiness", data.production_readiness.toString() + "%") {
            LinearProgressIndicator(progress = { data.production_readiness / 100f }, modifier = Modifier.fillMaxWidth())
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Metric("TESTERS", data.active_testers.toString() + " active", Modifier.weight(1f)) {
                Text(data.google_minimum.toString() + " minimum")
                Text(data.tester_target.toString() + " target")
                if (data.at_risk_testers > 0) Text(data.at_risk_testers.toString() + " need attention")
            }
            Metric("TESTING", "Day " + data.day + " / 14", Modifier.weight(1f)) {
                Text(data.days_remaining.toString() + " days remaining")
                Text("Ready: " + data.estimated_ready_date, style = MaterialTheme.typography.bodySmall)
            }
        }
        Metric("Circle health", if (data.circle_health == "GOOD") "Good" else "At risk") {
            Text(data.continuous_qualifying_testers.toString() + " continuous · " + data.replacement_testers + " replacement")
        }
        OutlinedButton(onClick = onGroupSetup, modifier = Modifier.fillMaxWidth()) {
            Text(
                "Google Group setup · " +
                    if (app.google_group_configured) "Confirmed" else "Not confirmed",
            )
        }
        if (data.testers_needed_for_minimum > 0) {
            Highlight {
                Text(data.active_testers.toString() + " / 12 testers", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text("Need " + data.testers_needed_for_minimum + " more to reach the minimum.")
                Text("Setup and invite tools remain available while your circle grows.")
            }
        }
        Button(onClick = onInvite, modifier = Modifier.fillMaxWidth()) { Text("Invite Developers") }
        OutlinedButton(onClick = onMatch, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("Match Available Testers") }
        OutlinedButton(onClick = onTesters, modifier = Modifier.fillMaxWidth()) { Text("View Tester Status") }
        Section("PROGRESS")
        Text("Missions · " + data.missions_completed + " / " + data.missions_total_available)
        Text("Feedback · " + data.feedback_count + " responses")
        OutlinedButton(onClick = onFeedback, modifier = Modifier.fillMaxWidth()) { Text("View Feedback") }
        Text(data.approval_disclaimer, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(20.dp))
    }
}

@Composable
private fun InviteScreen(invite: LaunchInvite?, loading: Boolean, onNew: () -> Unit, onClose: () -> Unit) {
    val context = LocalContext.current
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text("Invite Developers", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Join my Android testing circle", style = MaterialTheme.typography.titleLarge)
                Text("Help test my app and I’ll help test yours.")
                if (invite == null) {
                    CircularProgressIndicator()
                } else {
                    Text("Invite code")
                    Text(invite.invite_code, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                    OutlinedButton(onClick = { copy(context, invite.invite_code) }, modifier = Modifier.fillMaxWidth()) { Text("Copy invite code") }
                    OutlinedButton(onClick = { copy(context, invite.share_url) }, modifier = Modifier.fillMaxWidth()) { Text("Copy invite link") }
                    Button(onClick = { share(context, invite.share_url) }, modifier = Modifier.fillMaxWidth()) { Text("Share") }
                }
            }
        }
        OutlinedButton(onClick = onNew, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("Create another code") }
        OutlinedButton(onClick = onClose, modifier = Modifier.fillMaxWidth()) { Text("Done") }
    }
}

@Composable
private fun JoinScreen(loading: Boolean, onJoin: (String) -> Unit, onClose: () -> Unit) {
    var code by rememberSaveable { mutableStateOf("") }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text("Join Launch Circle", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("Enter the invite code another Android developer shared.")
        OutlinedTextField(
            code, { code = it.uppercase().take(8) },
            label = { Text("Invite code") }, placeholder = { Text("LC-8H4K2") },
            modifier = Modifier.fillMaxWidth(),
        )
        Button(onClick = { onJoin(code) }, enabled = !loading && code.isNotBlank(), modifier = Modifier.fillMaxWidth()) {
            Text("Join Launch Circle")
        }
        OutlinedButton(onClick = onClose, modifier = Modifier.fillMaxWidth()) { Text("Cancel") }
    }
}

@Composable
private fun JoinSuccess(config: PilotConfig, onAdd: () -> Unit, onTests: () -> Unit) {
    val uri = LocalUriHandler.current
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text("You’re in.", style = MaterialTheme.typography.displaySmall, fontWeight = FontWeight.Bold)
        Text("Next steps", style = MaterialTheme.typography.titleLarge)
        Text("1. Join the Launch Circle Google Group")
        Text("2. Add your Android app if you have one")
        Text("3. Start helping test other developers")
        Button(onClick = { uri.openUri(config.google_group_join_url) }, modifier = Modifier.fillMaxWidth()) { Text("Join Google Group") }
        OutlinedButton(onClick = onAdd, modifier = Modifier.fillMaxWidth()) { Text("Add My App") }
        OutlinedButton(onClick = onTests, modifier = Modifier.fillMaxWidth()) { Text("View Test Apps") }
    }
}

@Composable
private fun Today(
    missions: List<TestMission>,
    config: PilotConfig,
    onMission: (TestMission) -> Unit,
) {
    val uri = LocalUriHandler.current
    LazyColumn(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text("Today's Tests", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Text("Short, meaningful checks scheduled for today.")
            OutlinedButton(
                onClick = { uri.openUri(config.google_group_join_url) },
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
            ) { Text("Join Launch Circle Google Group") }
        }
        if (missions.isEmpty()) item { EmptyCard("You're caught up", "No missions are due. Check back on the next scheduled day.") }
        items(missions, key = { it.id }) { mission ->
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(mission.app_name, style = MaterialTheme.typography.titleLarge)
                    Text(pretty(mission.mission_type) + " Test")
                    Text("~" + mission.estimated_minutes + " min")
                    Button(onClick = { onMission(mission) }, modifier = Modifier.fillMaxWidth()) { Text("Start Test") }
                }
            }
        }
    }
}

@Composable
private fun Mission(
    mission: TestMission,
    onStart: () -> Unit,
    onOptIn: () -> Unit,
    onInstalled: () -> Unit,
    onSubmit: (Boolean, String, String?, String?) -> Unit,
) {
    val initial = when (mission.assignment_status) {
        "ACTIVE", "COMPLETED", "INSTALLED" -> 3
        "OPTED_IN" -> 2
        else -> 0
    }
    var step by rememberSaveable(mission.id) { mutableIntStateOf(initial) }
    var openOk by rememberSaveable(mission.id) { mutableStateOf<Boolean?>(null) }
    var featureOk by rememberSaveable(mission.id) { mutableStateOf<String?>(null) }
    var issue by rememberSaveable(mission.id) { mutableStateOf("") }
    var suggestion by rememberSaveable(mission.id) { mutableStateOf("") }
    val uri = LocalUriHandler.current
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(mission.app_name, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(pretty(mission.mission_type) + " Test", style = MaterialTheme.typography.titleLarge)
        Text("About " + mission.estimated_minutes + " minutes")
        if (step == 0) Button(onClick = { uri.openUri(mission.opt_in_url); step = 1 }, modifier = Modifier.fillMaxWidth()) { Text("Open Play Testing Link") }
        if (step == 1) Button(onClick = { onOptIn(); step = 2 }, modifier = Modifier.fillMaxWidth()) { Text("Confirm Opt-In") }
        if (step == 2) Button(onClick = { onInstalled(); step = 3 }, modifier = Modifier.fillMaxWidth()) { Text("Confirm Installed") }
        if (step == 3) {
            Highlight { Text("Your mission", fontWeight = FontWeight.SemiBold); Text(missionPrompt(mission.mission_type)) }
            Button(onClick = { onStart(); step = 4 }, modifier = Modifier.fillMaxWidth()) { Text("Complete Mission") }
        }
        if (step >= 4) {
            Text("Did the app open successfully?", fontWeight = FontWeight.SemiBold)
            Choices(listOf("Yes", "No"), openOk?.let { if (it) "Yes" else "No" }) { openOk = it == "Yes" }
            Text("Did the main feature work?", fontWeight = FontWeight.SemiBold)
            Choices(listOf("Yes", "Partly", "No"), featureOk?.lowercase()?.replaceFirstChar { it.uppercase() }) { featureOk = it.uppercase() }
            OutlinedTextField(issue, { issue = it }, label = { Text("Any issue? Optional") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(suggestion, { suggestion = it }, label = { Text("Any suggestion? Optional") }, modifier = Modifier.fillMaxWidth())
            Button(
                onClick = { onSubmit(checkNotNull(openOk), checkNotNull(featureOk), issue, suggestion) },
                enabled = openOk != null && featureOk != null,
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Submit Feedback") }
        }
    }
}

@Composable
private fun Testers(rows: List<TesterAssignment>) {
    val active = rows.count { it.status in setOf("ACTIVE", "COMPLETED") && it.health_status in setOf("GOOD", "NEW") }
    val attention = rows.count { it.health_status in setOf("AT_RISK", "INACTIVE") }
    LazyColumn(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Text("Tester Status", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Text(active.toString() + " active · " + attention + " need attention · " + rows.count { it.is_replacement } + " replacement")
        }
        items(rows, key = { it.id }) { tester ->
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(tester.tester_label, style = MaterialTheme.typography.titleMedium)
                        StatusChip(testerLabel(tester))
                    }
                    Text("Day " + tester.testing_day)
                    Text(tester.completed_missions.toString() + " / " + tester.total_missions + " missions")
                    if (tester.is_replacement) Text("Fresh testing timeline", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

@Composable
private fun Feedback(rows: List<MissionFeedback>) {
    LazyColumn(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item { Text("Feedback", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold) }
        if (rows.isEmpty()) item { EmptyCard("No feedback yet", "Responses appear after completed missions.") }
        items(rows, key = { it.id }) { row ->
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(row.tester_label + " · " + pretty(row.mission_type), fontWeight = FontWeight.SemiBold)
                    row.issue_text?.let { Text("Issue · " + it) }
                    row.suggestion_text?.let { Text("Suggestion · " + it) }
                }
            }
        }
    }
}

@Composable
private fun Metric(label: String, value: String, modifier: Modifier = Modifier, content: @Composable () -> Unit = {}) {
    Card(modifier) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Section(label)
            Text(value, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            content()
        }
    }
}

@Composable
private fun Highlight(content: @Composable ColumnScope.() -> Unit) {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(7.dp), content = content)
    }
}

@Composable
private fun Option(selected: Boolean, title: String, body: String, onClick: () -> Unit) {
    OutlinedCard(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.outlinedCardColors(
            containerColor = if (selected) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surface,
        ),
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(title, fontWeight = FontWeight.SemiBold)
            Text(body, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun StatusChip(text: String) {
    Surface(color = MaterialTheme.colorScheme.secondaryContainer, shape = RoundedCornerShape(50)) {
        Text(text, modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp), style = MaterialTheme.typography.labelMedium)
    }
}

@Composable
private fun Section(text: String) {
    Text(text, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
}

@Composable
private fun EmptyCard(title: String, body: String) {
    OutlinedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, style = MaterialTheme.typography.titleLarge)
            Text(body, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun ErrorBanner(message: String) {
    Surface(color = MaterialTheme.colorScheme.errorContainer, modifier = Modifier.fillMaxWidth()) {
        Text(message, modifier = Modifier.padding(12.dp), color = MaterialTheme.colorScheme.onErrorContainer)
    }
}

@Composable
private fun Choices(values: List<String>, selected: String?, onSelect: (String) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
        values.forEach { value ->
            if (value == selected) Button(onClick = { onSelect(value) }) { Text(value) }
            else OutlinedButton(onClick = { onSelect(value) }) { Text(value) }
        }
    }
}

private fun testerLabel(value: TesterAssignment): String = when {
    value.status == "DROPPED" || value.health_status == "DROPPED" -> "Dropped"
    value.health_status == "INACTIVE" -> "Inactive"
    value.health_status == "AT_RISK" -> "Needs attention"
    value.is_replacement -> "Replacement"
    value.health_status == "NEW" -> "New"
    else -> "Active"
}

private fun missionPrompt(type: String): String = when (type) {
    "INSTALL_FIRST_IMPRESSION" -> "Check the first-run experience."
    "CORE_FEATURE" -> "Use the main feature and note anything unclear."
    "EDGE_CASE" -> "Try an unusual input or interruption."
    "SECOND_USE" -> "Return and complete a normal task again."
    "RETEST" -> "Recheck the latest developer changes."
    "FINAL_FEEDBACK" -> "Summarize the full testing experience."
    else -> pretty(type)
}

private fun pretty(value: String): String =
    value.lowercase().split("_").joinToString(" ") { it.replaceFirstChar(Char::uppercase) }

private fun copy(context: Context, value: String) {
    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    clipboard.setPrimaryClip(ClipData.newPlainText("Launch Circle", value))
}

private fun share(context: Context, value: String) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_TEXT, "Join my Android testing circle\n\n" + value)
    }
    context.startActivity(Intent.createChooser(intent, "Share invite"))
}
