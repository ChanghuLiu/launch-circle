package com.launchcircle.testers.feature.launch

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Groups
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material.icons.rounded.RocketLaunch
import androidx.compose.material.icons.rounded.Science
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchDashboard
import com.launchcircle.testers.core.model.LaunchInvite
import com.launchcircle.testers.core.model.LaunchCircle
import com.launchcircle.testers.core.model.MissionFeedback
import com.launchcircle.testers.core.model.PilotConfig
import com.launchcircle.testers.core.model.TestMission
import com.launchcircle.testers.core.model.TestAssignment
import com.launchcircle.testers.core.model.TesterAssignment
import com.launchcircle.testers.core.model.UserProfile
import com.launchcircle.testers.feature.onboarding.AccountScreen
import com.launchcircle.testers.ui.theme.LaunchAttention

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
    val primaryDestination = state.pilotSurface == PilotSurface.NONE && state.destination in setOf(
        LaunchDestination.MY_LAUNCHES,
        LaunchDestination.DASHBOARD,
        LaunchDestination.TODAY_TESTS,
        LaunchDestination.TESTERS,
    )
    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        contentWindowInsets = WindowInsets.safeDrawing,
        bottomBar = {
            if (primaryDestination) {
                LaunchNavigation(
                    destination = state.destination,
                    onHome = viewModel::showMyLaunch,
                    onTests = viewModel::showToday,
                    onMyLaunch = viewModel::showHome,
                    onCircle = viewModel::showCircle,
                )
            }
        },
    ) { contentPadding ->
        Column(Modifier.fillMaxSize().padding(contentPadding)) {
            if (state.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
            if (state.pilotSurface == PilotSurface.NONE && !primaryDestination &&
                state.destination != LaunchDestination.ACCOUNT
            ) {
                TextButton(
                    onClick = viewModel::back,
                    modifier = Modifier.defaultMinSize(minHeight = 48.dp).padding(horizontal = 8.dp),
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
                        {
                            viewModel.closePilotSurface()
                            viewModel.showCircle()
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
                            profile, state.launches, state.dashboards, state.selectedApp, state.todayAssignments,
                            viewModel::showAddApp, viewModel::showDashboard,
                            viewModel::showToday, viewModel::showAssignment, viewModel::showInvite,
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
                            state.todayAssignments, state.pilotConfig, viewModel::showAssignment,
                        )
                        LaunchDestination.ASSIGNMENT -> state.selectedAssignment?.let {
                            AssignmentScreen(it, viewModel::completeAssignment)
                        }
                        LaunchDestination.MISSION -> state.selectedMission?.let {
                            Mission(
                                it, viewModel::startMission, viewModel::confirmOptIn,
                                viewModel::confirmInstalled, viewModel::submitFeedback,
                            )
                        }
                        LaunchDestination.TESTERS -> Testers(
                            app = state.selectedApp,
                            dashboard = state.selectedApp?.let { state.dashboards[it.id] },
                            rows = state.testers,
                            circle = state.circle,
                        )
                        LaunchDestination.FEEDBACK -> Feedback(state.feedback)
                        LaunchDestination.ACCOUNT -> AccountScreen(
                            profile = profile,
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
private fun LaunchNavigation(
    destination: LaunchDestination,
    onHome: () -> Unit,
    onTests: () -> Unit,
    onMyLaunch: () -> Unit,
    onCircle: () -> Unit,
) {
    data class Item(
        val label: String,
        val icon: androidx.compose.ui.graphics.vector.ImageVector,
        val selected: Boolean,
        val onClick: () -> Unit,
    )
    val items = listOf(
        Item("Home", Icons.Rounded.Home, destination == LaunchDestination.MY_LAUNCHES, onHome),
        Item("Tests", Icons.Rounded.Science, destination == LaunchDestination.TODAY_TESTS, onTests),
        Item("My Launch", Icons.Rounded.RocketLaunch, destination == LaunchDestination.DASHBOARD, onMyLaunch),
        Item("Circle", Icons.Rounded.Groups, destination == LaunchDestination.TESTERS, onCircle),
    )
    NavigationBar(containerColor = MaterialTheme.colorScheme.surfaceContainerLow) {
        items.forEach { item ->
            NavigationBarItem(
                selected = item.selected,
                onClick = item.onClick,
                icon = { Icon(item.icon, contentDescription = null) },
                label = { Text(item.label, maxLines = 1) },
            )
        }
    }
}

@Composable
private fun Home(
    profile: UserProfile,
    apps: List<LaunchApp>,
    dashboards: Map<String, LaunchDashboard>,
    selectedApp: LaunchApp?,
    today: List<TestAssignment>,
    onAdd: () -> Unit,
    onOpen: (LaunchApp) -> Unit,
    onToday: () -> Unit,
    onAssignment: (TestAssignment) -> Unit,
    onInvite: () -> Unit,
    onJoin: () -> Unit,
    onAccount: () -> Unit,
    onLogout: () -> Unit,
) {
    val primaryApp = selectedApp ?: apps.firstOrNull()
    val dashboard = primaryApp?.let { dashboards[it.id] }
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp),
    ) {
        item {
            Text("Home", style = MaterialTheme.typography.headlineLarge)
            Text("Welcome back, " + (profile.display_name ?: "developer"), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (primaryApp == null || dashboard == null) {
            item {
                EmptyCard(
                    "Your first launch starts here",
                    "Add an app, connect tester access, then invite developers or match available testers.",
                )
            }
            item {
                MetricCard(
                    label = "Today's Work",
                    value = "${today.size} ${if (today.size == 1) "test" else "tests"}",
                    supporting = "~${today.sumOf { it.estimated_minutes }} min",
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            item { Button(onClick = onAdd, modifier = Modifier.fillMaxWidth()) { Text("Add app") } }
        } else {
            item {
                CountdownHero(primaryApp, dashboard) { onOpen(primaryApp) }
            }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    MetricCard(
                        label = "Tester Coverage",
                        value = "${dashboard.active_testers} / ${dashboard.google_minimum}",
                        supporting = if (dashboard.testers_needed_for_minimum == 0) "Requirement met" else
                            "${dashboard.testers_needed_for_minimum} more required",
                        positive = dashboard.testers_needed_for_minimum == 0,
                        modifier = Modifier.weight(1f),
                    )
                    MetricCard(
                        label = "Today's Work",
                        value = "${today.size} ${if (today.size == 1) "test" else "tests"}",
                        supporting = "~${today.sumOf { it.estimated_minutes }} min",
                        modifier = Modifier.weight(1f),
                    )
                }
            }
            item {
                SectionHeader("TODAY", if (today.isNotEmpty()) "View all" else null, onToday)
            }
            if (today.isEmpty()) {
                item { EmptyCard("You're caught up", "No tests are assigned for today.") }
            } else {
                items(today, key = { "home-${it.id}" }) { mission ->
                    TodayAssignmentCard(assignment = mission, onClick = { onAssignment(mission) }, compact = true)
                }
            }
            item {
                SectionHeader("CIRCLE HEALTH")
                HealthCard(dashboard)
            }
            item {
                SectionHeader("YOUR LAUNCHES")
            }
            items(apps, key = { it.id }) { app ->
                LaunchCard(app, dashboards[app.id]) { onOpen(app) }
            }
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                SecondaryLaunchButton("Invite developers", onInvite)
                SecondaryLaunchButton("Join with invite code", onJoin)
                TextButton(onClick = onAccount, modifier = Modifier.fillMaxWidth()) { Text("Account & settings") }
                TextButton(onClick = onLogout, modifier = Modifier.fillMaxWidth()) { Text("Sign out") }
            }
        }
    }
}

@Composable
private fun CountdownHero(app: LaunchApp, dashboard: LaunchDashboard, onOpen: () -> Unit) {
    val onTrack = dashboard.circle_health == "GOOD" && dashboard.testers_needed_for_minimum == 0
    val totalDays = dashboard.total_days.coerceAtLeast(1)
    Card(
        onClick = onOpen,
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.onPrimary,
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
    ) {
        Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
            ) {
                Text(
                    app.name,
                    modifier = Modifier.weight(1f),
                    style = MaterialTheme.typography.titleLarge,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(Modifier.width(12.dp))
                StatusBadge(if (onTrack) "Testing on track" else "Needs attention", if (onTrack) StatusTone.SUCCESS else StatusTone.ATTENTION)
            }
            Column(verticalArrangement = Arrangement.spacedBy(0.dp)) {
                if (dashboard.testing_started_at == null) {
                    Text(
                        "Waiting for testers",
                        style = MaterialTheme.typography.headlineMedium,
                    )
                    Text(
                        "${dashboard.qualifying_tester_count} / ${dashboard.required_tester_count} ready",
                        style = MaterialTheme.typography.titleLarge,
                    )
                    Text("Day 1 starts when the requirement is met.", style = MaterialTheme.typography.bodyLarge)
                } else if (dashboard.lifecycle_complete) {
                    Text("Internal testing complete", style = MaterialTheme.typography.headlineMedium)
                    Text("Production application can be prepared.", style = MaterialTheme.typography.bodyLarge)
                } else {
                    Text(
                        dashboard.days_remaining.coerceAtLeast(0).toString(),
                        style = MaterialTheme.typography.displayLarge.copy(fontSize = 72.sp, lineHeight = 76.sp),
                    )
                    Text("DAYS", style = MaterialTheme.typography.titleLarge)
                    Text("until internal testing eligibility", style = MaterialTheme.typography.bodyLarge)
                }
            }
            Text(
                if (dashboard.testing_started_at == null) {
                    "Waiting for Day 1"
                } else {
                    "Day ${dashboard.day.coerceAtLeast(0)} of $totalDays"
                },
                style = MaterialTheme.typography.titleMedium,
            )
            LinearProgressIndicator(
                progress = {
                    if (dashboard.testing_started_at == null) 0f
                    else dashboard.elapsed_days.coerceIn(0, totalDays) / totalDays.toFloat()
                },
                modifier = Modifier.fillMaxWidth().height(10.dp),
                color = MaterialTheme.colorScheme.onPrimary,
                trackColor = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.24f),
            )
            Text(
                "${dashboard.qualifying_tester_count} / ${dashboard.required_tester_count} testers qualifying",
                style = MaterialTheme.typography.titleMedium,
            )
        }
    }
}

@Composable
private fun MetricCard(
    label: String,
    value: String,
    supporting: String,
    positive: Boolean = false,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(label, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.headlineSmall)
            Text(
                supporting,
                style = MaterialTheme.typography.bodyMedium,
                color = if (positive) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun HealthCard(dashboard: LaunchDashboard) {
    val good = dashboard.circle_health == "GOOD"
    OutlinedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(if (good) "Good" else "Action needed", style = MaterialTheme.typography.headlineSmall)
                StatusBadge(if (good) "Healthy" else "Attention", if (good) StatusTone.SUCCESS else StatusTone.ATTENTION)
            }
            Text("${dashboard.active_testers} active testers", color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (dashboard.at_risk_testers > 0) {
                Text("${dashboard.at_risk_testers} need attention", color = LaunchAttention)
            }
        }
    }
}

@Composable
private fun LaunchCard(app: LaunchApp, dashboard: LaunchDashboard?, onOpen: () -> Unit) {
    OutlinedCard(
        onClick = onOpen,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(app.name, style = MaterialTheme.typography.titleLarge, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Day ${dashboard?.day ?: 0} / ${dashboard?.total_days ?: 14}")
                Text("${dashboard?.active_testers ?: 0} active", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            LinearProgressIndicator(
                progress = { (dashboard?.production_readiness ?: 0).coerceIn(0, 100) / 100f },
                modifier = Modifier.fillMaxWidth(),
            )
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
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Text("My Launch", style = MaterialTheme.typography.headlineLarge)
            Text(
                app.name,
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        item {
            Card(
                Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
            ) {
                Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(
                            if (data.testing_started_at == null) "Waiting for testers"
                            else "Day ${data.day} / ${data.total_days}",
                            style = MaterialTheme.typography.headlineMedium,
                        )
                        StatusBadge(pretty(data.status))
                    }
                    LinearProgressIndicator(
                        progress = { data.production_readiness.coerceIn(0, 100) / 100f },
                        modifier = Modifier.fillMaxWidth().height(8.dp),
                        drawStopIndicator = {},
                    )
                    Text(
                        if (data.testing_started_at == null) {
                            "${data.qualifying_tester_count} / ${data.required_tester_count} ready"
                        } else if (data.lifecycle_complete) {
                            "14-day internal test complete"
                        } else {
                            "${data.days_remaining.coerceAtLeast(0)} days remaining"
                        },
                        style = MaterialTheme.typography.titleMedium,
                    )
                    if (data.estimated_ready_date.isNotBlank()) {
                        Text("Estimated production date · ${data.estimated_ready_date}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    if (data.replacement_status != "NONE") {
                        Text(
                            when (data.replacement_status) {
                                "COVERAGE_RESTORED" -> "Coverage restored"
                                "REPLACEMENT_ASSIGNED" -> "Replacement assigned"
                                else -> "Coverage at risk"
                            },
                            color = if (data.coverage_shortage == 0) MaterialTheme.colorScheme.tertiary else LaunchAttention,
                        )
                    }
                    if (data.risk_reason.isNotBlank()) {
                        Text(data.risk_reason, color = LaunchAttention)
                    }
                }
            }
        }
        item {
            SectionHeader("TESTER COVERAGE")
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                MetricCard("Active testers", data.qualifying_tester_count.toString(), "Currently qualifying", data.qualifying_tester_count >= data.required_tester_count, Modifier.fillMaxWidth())
                MetricCard("Required testers", data.required_tester_count.toString(), "Launch Circle requirement", modifier = Modifier.fillMaxWidth())
            }
        }
        item {
            SectionHeader("MILESTONES")
            MilestoneTimeline(data)
        }
        item {
            SectionHeader("CIRCLE HEALTH")
            HealthCard(data)
        }
        item {
            OutlinedButton(onClick = onGroupSetup, modifier = Modifier.fillMaxWidth()) {
                Text("Tester access · " + if (app.google_group_configured) "Confirmed" else "Setup needed")
            }
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onInvite, modifier = Modifier.fillMaxWidth()) { Text("Invite developers") }
                OutlinedButton(onClick = onMatch, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("Match available testers") }
                OutlinedButton(onClick = onTesters, modifier = Modifier.fillMaxWidth()) { Text("View circle") }
            }
        }
        item {
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Activity", style = MaterialTheme.typography.titleMedium)
                    Text("Missions · ${data.missions_completed} / ${data.missions_total_available}")
                    Text("Feedback · ${data.feedback_count} responses")
                    TextButton(onClick = onFeedback) { Text("View feedback") }
                }
            }
        }
        item {
            Text(data.approval_disclaimer, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun MilestoneTimeline(data: LaunchDashboard) {
    val milestones = listOf(
        Triple("Tester requirement", "${data.qualifying_tester_count} / ${data.required_tester_count} active", data.qualifying_tester_count >= data.required_tester_count),
        Triple("14-day closed test", "Day ${data.day} of ${data.total_days}", data.lifecycle_complete),
        Triple("Production review", "After testing requirements are complete", data.internally_production_ready),
    )
    OutlinedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(horizontal = 18.dp)) {
            milestones.forEachIndexed { index, (title, detail, complete) ->
                Row(Modifier.fillMaxWidth().padding(vertical = 16.dp)) {
                    Text(if (complete) "✓" else (index + 1).toString(), color = if (complete) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.primary)
                    Spacer(Modifier.width(14.dp))
                    Column(Modifier.weight(1f)) {
                        Text(title, style = MaterialTheme.typography.titleMedium)
                        Text(detail, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                if (index != milestones.lastIndex) HorizontalDivider()
            }
        }
    }
}

@Composable
private fun InviteScreen(invite: LaunchInvite?, loading: Boolean, onNew: () -> Unit, onClose: () -> Unit) {
    val context = LocalContext.current
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        TextButton(
            onClick = onClose,
            modifier = Modifier.defaultMinSize(minHeight = 48.dp),
        ) { Text("Back") }
        Text("Invite Developers", style = MaterialTheme.typography.headlineLarge)
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Grow your testing circle", style = MaterialTheme.typography.titleLarge)
            Text(
                "Invite another Android developer. You test their app. They test yours.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Card(
            Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        ) {
            Column(
                Modifier.fillMaxWidth().padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                if (invite == null) {
                    CircularProgressIndicator()
                } else {
                    Text("YOUR INVITE CODE", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onPrimaryContainer)
                    Text(
                        invite.invite_code,
                        style = MaterialTheme.typography.displaySmall.copy(fontFamily = FontFamily.Monospace),
                        maxLines = 1,
                    )
                    PrimaryLaunchButton("Share invite", onClick = { share(context, invite.share_url) })
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                        TextButton(onClick = { copy(context, invite.share_url) }) { Text("Copy link") }
                        TextButton(onClick = { copy(context, invite.invite_code) }) { Text("Copy code") }
                    }
                }
            }
        }
        SecondaryLaunchButton("Create another code", onNew, enabled = !loading)
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
private fun JoinSuccess(
    config: PilotConfig,
    onAdd: () -> Unit,
    onTests: () -> Unit,
    onCircle: () -> Unit,
) {
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
        OutlinedButton(onClick = onCircle, modifier = Modifier.fillMaxWidth()) { Text("View Circle Members") }
    }
}

@Composable
private fun Today(
    assignments: List<TestAssignment>,
    config: PilotConfig,
    onAssignment: (TestAssignment) -> Unit,
) {
    val uri = LocalUriHandler.current
    val completed = assignments.filter { it.status == "COMPLETED" || it.completed_at != null }
    val toDo = assignments.filterNot { it.status == "COMPLETED" || it.completed_at != null }
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text("Tests", style = MaterialTheme.typography.headlineLarge)
            Text("Today's tests", style = MaterialTheme.typography.titleLarge, modifier = Modifier.padding(top = 4.dp))
            Text("Short, meaningful checks scheduled for today.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            OutlinedButton(
                onClick = { uri.openUri(config.google_group_join_url) },
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
            ) { Text("Open Launch Circle Google Group") }
        }
        if (assignments.isEmpty()) item { EmptyCard("You're caught up", "No tests are assigned for today.") }
        if (toDo.isNotEmpty()) item { SectionHeader("TO DO") }
        items(toDo, key = { "todo-${it.id}" }) { assignment ->
            TodayAssignmentCard(assignment, { onAssignment(assignment) })
        }
        if (completed.isNotEmpty()) item { SectionHeader("COMPLETED") }
        items(completed, key = { "completed-${it.id}" }) { assignment ->
            TodayAssignmentCard(assignment, { onAssignment(assignment) }, completed = true)
        }
    }
}

private enum class MissionCategory { TO_DO, IN_PROGRESS, COMPLETED }

private fun missionCategory(mission: TestMission): MissionCategory = when {
    mission.status == "COMPLETED" || mission.completed_at != null -> MissionCategory.COMPLETED
    mission.status == "IN_PROGRESS" || mission.assignment_status in setOf("OPTED_IN", "INSTALLED") -> MissionCategory.IN_PROGRESS
    else -> MissionCategory.TO_DO
}

@Composable
private fun TodayMissionCard(
    mission: TestMission,
    onClick: () -> Unit,
    compact: Boolean = false,
    inProgress: Boolean = false,
    completed: Boolean = false,
) {
    val container = if (completed) MaterialTheme.colorScheme.surfaceContainerLow else MaterialTheme.colorScheme.surfaceContainerLowest
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = container),
        elevation = CardDefaults.cardElevation(defaultElevation = if (completed) 0.dp else 1.dp),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                AppAvatar(mission.app_name, muted = completed)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(
                        mission.app_name,
                        style = MaterialTheme.typography.titleMedium,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        color = if (completed) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurface,
                    )
                    Text(
                        pretty(mission.mission_type) + " test",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("~${mission.estimated_minutes} min", style = MaterialTheme.typography.labelLarge)
                    if (compact && !completed) {
                        Button(onClick = onClick, modifier = Modifier.defaultMinSize(minHeight = 48.dp)) { Text("Start") }
                    } else if (!completed) {
                        FilledTonalButton(onClick = onClick, modifier = Modifier.defaultMinSize(minHeight = 48.dp)) {
                            Text(if (inProgress) "Continue" else "Start test")
                        }
                    }
                }
            }
            if (completed) Text("Completed", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.tertiary)
        }
    }
}

@Composable
private fun TodayAssignmentCard(
    assignment: TestAssignment,
    onClick: () -> Unit,
    compact: Boolean = false,
    completed: Boolean = false,
) {
    val container = if (completed) MaterialTheme.colorScheme.surfaceContainerLow else MaterialTheme.colorScheme.surfaceContainerLowest
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = container),
        elevation = CardDefaults.cardElevation(defaultElevation = if (completed) 0.dp else 1.dp),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                AppAvatar(assignment.app_name, muted = completed)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(
                        assignment.app_name,
                        style = MaterialTheme.typography.titleMedium,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        color = if (completed) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurface,
                    )
                    Text(pretty(assignment.test_type) + " test", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("~${assignment.estimated_minutes} min", style = MaterialTheme.typography.labelLarge)
                    if (completed) {
                        Text("Completed", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.tertiary)
                    } else {
                        val label = if (compact) "Start" else "Start test"
                        FilledTonalButton(onClick = onClick, modifier = Modifier.defaultMinSize(minHeight = 48.dp)) { Text(label) }
                    }
                }
            }
        }
    }
}

@Composable
private fun AssignmentScreen(assignment: TestAssignment, onComplete: () -> Unit) {
    val uri = LocalUriHandler.current
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(assignment.app_name, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(pretty(assignment.test_type) + " Test", style = MaterialTheme.typography.titleLarge)
        Text("About ${assignment.estimated_minutes} minutes")
        Text("Assigned for ${assignment.assignment_day}", color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (assignment.status == "COMPLETED" || assignment.completed_at != null) {
            Highlight { Text("Completed", fontWeight = FontWeight.SemiBold); Text("Your completion is saved.") }
        } else {
            Button(onClick = { uri.openUri(assignment.opt_in_url) }, modifier = Modifier.fillMaxWidth()) {
                Text("Start test")
            }
            Button(onClick = onComplete, modifier = Modifier.fillMaxWidth()) { Text("Mark test complete") }
        }
    }
}

@Composable
private fun AppAvatar(name: String, muted: Boolean = false) {
    val initials = name.split(Regex("\\s+")).filter { it.isNotBlank() }.take(2)
        .joinToString("") { it.take(1).uppercase() }.ifBlank { "A" }
    Surface(
        modifier = Modifier.size(48.dp),
        shape = RoundedCornerShape(14.dp),
        color = if (muted) MaterialTheme.colorScheme.surfaceContainerHigh else MaterialTheme.colorScheme.primaryContainer,
        contentColor = if (muted) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onPrimaryContainer,
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(initials, style = MaterialTheme.typography.titleMedium)
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
private fun Testers(
    app: LaunchApp?,
    dashboard: LaunchDashboard?,
    rows: List<TesterAssignment>,
    circle: LaunchCircle?,
) {
    val attentionRows = rows.filter { participationState(it) == "NEEDS_ATTENTION" }
    val inactiveRows = rows.filter { participationState(it) == "INACTIVE" }
    val droppedRows = rows.filter { participationState(it) == "DROPPED" }
    val activeRows = rows.filter { participationState(it) == "ACTIVE" }
    val active = dashboard?.active_testers ?: activeRows.size
    val attention = dashboard?.at_risk_testers ?: attentionRows.size + inactiveRows.size
    val healthy = dashboard?.status != "AT_RISK" && dashboard?.circle_health == "GOOD"
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text("Circle", style = MaterialTheme.typography.headlineLarge)
            Text(
                app?.let { "${it.name} testing circle" } ?: "Testing circle",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        item {
            Card(
                Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLowest),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
            ) {
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text("Circle Health", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(if (healthy) "Healthy" else "Needs attention", style = MaterialTheme.typography.headlineSmall)
                        }
                        StatusBadge(if (healthy) "On track" else "Attention", if (healthy) StatusTone.SUCCESS else StatusTone.ATTENTION)
                    }
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Tester coverage", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("$active / ${dashboard?.required_tester_count ?: 12}", style = MaterialTheme.typography.labelLarge)
                    }
                    LinearProgressIndicator(
                        progress = {
                            val target = dashboard?.required_tester_count?.coerceAtLeast(1) ?: active.coerceAtLeast(1)
                            active.coerceIn(0, target) / target.toFloat()
                        },
                        modifier = Modifier.fillMaxWidth().height(8.dp),
                        color = if (healthy) MaterialTheme.colorScheme.tertiary else LaunchAttention,
                    )
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        CircleMetric(active.toString(), "Active", StatusTone.SUCCESS, Modifier.weight(1f))
                        CircleMetric(attention.toString(), "Attention", StatusTone.ATTENTION, Modifier.weight(1f))
                        CircleMetric(droppedRows.size.toString(), "Dropped", StatusTone.NEUTRAL, Modifier.weight(1f))
                    }
                }
            }
        }
        if (app != null) {
            item {
                SectionHeader("APP STATUS")
                OutlinedCard(Modifier.fillMaxWidth()) {
                    Row(
                        Modifier.fillMaxWidth().padding(18.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text(
                            app.name,
                            modifier = Modifier.weight(1f),
                            style = MaterialTheme.typography.titleMedium,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Spacer(Modifier.width(8.dp))
                        StatusBadge(pretty(dashboard?.status ?: app.status))
                    }
                }
            }
        }
        circle?.let { launchCircle ->
            item {
                SectionHeader("CIRCLE MEMBERS")
                Text(
                    "${launchCircle.active_member_count} / ${launchCircle.max_members} active members",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            items(launchCircle.members, key = { "circle-${it.id}" }) { member ->
                OutlinedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(member.member_label, style = MaterialTheme.typography.titleMedium)
                        Text(
                            if (member.role == "OWNER") "Circle owner"
                            else if (member.status == "ACTIVE") "Active member"
                            else member.status.lowercase().replaceFirstChar { it.uppercase() } + " member",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
        if (rows.isEmpty()) item { EmptyCard("No tester statuses yet", "Tester status appears after members are assigned to this app.") }
        if (attentionRows.isNotEmpty()) item { SectionHeader("NEEDS ATTENTION") }
        items(attentionRows, key = { "attention-${it.id}" }) { tester ->
            TesterStatusRow(tester)
        }
        if (activeRows.isNotEmpty()) item { SectionHeader("ACTIVE MEMBERS") }
        items(activeRows, key = { "active-${it.id}" }) { tester ->
            TesterStatusRow(tester)
        }
        if (inactiveRows.isNotEmpty()) item { SectionHeader("INACTIVE") }
        items(inactiveRows, key = { "inactive-${it.id}" }) { tester ->
            TesterStatusRow(tester, muted = true)
        }
        if (droppedRows.isNotEmpty()) item { SectionHeader("DROPPED") }
        items(droppedRows, key = { "dropped-${it.id}" }) { tester ->
            TesterStatusRow(tester, muted = true)
        }
    }
}

@Composable
private fun CircleMetric(value: String, label: String, tone: StatusTone, modifier: Modifier = Modifier) {
    val color = when (tone) {
        StatusTone.SUCCESS -> MaterialTheme.colorScheme.tertiary
        StatusTone.ATTENTION -> LaunchAttention
        StatusTone.NEUTRAL -> MaterialTheme.colorScheme.onSurfaceVariant
    }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(value, style = MaterialTheme.typography.headlineSmall, color = color)
        Text(label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

private fun participationState(tester: TesterAssignment): String = when {
    tester.status == "DROPPED" || tester.health_status == "DROPPED" -> "DROPPED"
    tester.health_status == "INACTIVE" -> "INACTIVE"
    tester.health_status == "AT_RISK" -> "NEEDS_ATTENTION"
    tester.participation_state.isNotBlank() -> tester.participation_state
    else -> "ACTIVE"
}

@Composable
private fun TesterStatusRow(tester: TesterAssignment, muted: Boolean = false) {
    OutlinedCard(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.outlinedCardColors(
            containerColor = if (muted) MaterialTheme.colorScheme.surfaceContainerLow else MaterialTheme.colorScheme.surfaceContainerLowest,
        ),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            TesterAvatar(tester.tester_label, muted)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(
                    tester.tester_label,
                    style = MaterialTheme.typography.titleMedium,
                    color = if (muted) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurface,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text("Day ${tester.testing_day}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (tester.total_missions > 0) {
                    Text("${tester.completed_missions} / ${tester.total_missions} tests", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            StatusBadge(testerLabel(tester), testerTone(tester))
        }
    }
}

@Composable
private fun TesterAvatar(label: String, muted: Boolean) {
    val marker = label.substringAfterLast("#", label).trim().take(2).ifBlank { "T" }
    Surface(
        modifier = Modifier.size(44.dp),
        shape = CircleShape,
        color = if (muted) MaterialTheme.colorScheme.surfaceContainerHigh else MaterialTheme.colorScheme.secondaryContainer,
        contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
    ) {
        Box(contentAlignment = Alignment.Center) { Text(marker, style = MaterialTheme.typography.titleMedium) }
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

private enum class StatusTone { NEUTRAL, SUCCESS, ATTENTION }

@Composable
private fun StatusBadge(text: String, tone: StatusTone = StatusTone.NEUTRAL) {
    val containerColor = when (tone) {
        StatusTone.NEUTRAL -> MaterialTheme.colorScheme.secondaryContainer
        StatusTone.SUCCESS -> MaterialTheme.colorScheme.tertiaryContainer
        StatusTone.ATTENTION -> androidx.compose.ui.graphics.Color(0xFFFFDDB0)
    }
    val contentColor = when (tone) {
        StatusTone.NEUTRAL -> MaterialTheme.colorScheme.onSecondaryContainer
        StatusTone.SUCCESS -> MaterialTheme.colorScheme.onTertiaryContainer
        StatusTone.ATTENTION -> androidx.compose.ui.graphics.Color(0xFF5F3B00)
    }
    Surface(color = containerColor, contentColor = contentColor, shape = RoundedCornerShape(50)) {
        Text(
            text,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            style = MaterialTheme.typography.labelMedium,
            maxLines = 2,
        )
    }
}

@Composable
private fun SectionHeader(text: String, action: String? = null, onAction: () -> Unit = {}) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Section(text)
        if (action != null) {
            TextButton(onClick = onAction, modifier = Modifier.defaultMinSize(minHeight = 48.dp)) { Text(action) }
        }
    }
}

@Composable
private fun PrimaryLaunchButton(text: String, onClick: () -> Unit, enabled: Boolean = true) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.fillMaxWidth().defaultMinSize(minHeight = 52.dp),
    ) { Text(text) }
}

@Composable
private fun SecondaryLaunchButton(text: String, onClick: () -> Unit, enabled: Boolean = true) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.fillMaxWidth().defaultMinSize(minHeight = 52.dp),
    ) { Text(text) }
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
    participationState(value) == "DROPPED" -> "Dropped"
    participationState(value) == "INACTIVE" -> "Inactive"
    participationState(value) == "NEEDS_ATTENTION" -> "Needs attention"
    value.is_replacement -> "Replacement"
    value.health_status == "NEW" -> "New"
    else -> "Active"
}

private fun testerTone(value: TesterAssignment): StatusTone = when {
    participationState(value) == "ACTIVE" -> StatusTone.SUCCESS
    participationState(value) in setOf("NEEDS_ATTENTION", "INACTIVE") -> StatusTone.ATTENTION
    else -> StatusTone.NEUTRAL
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
