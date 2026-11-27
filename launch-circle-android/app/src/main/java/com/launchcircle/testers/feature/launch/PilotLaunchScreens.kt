package com.launchcircle.testers.feature.launch

import androidx.compose.ui.graphics.asImageBitmap
import androidx.core.graphics.drawable.toBitmap
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
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Groups
import androidx.compose.material.icons.rounded.Apps
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material.icons.rounded.RocketLaunch
import androidx.compose.material.icons.rounded.Science
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
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
import androidx.activity.compose.LocalActivity
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.launchcircle.testers.core.model.AdditionalAppCheckout
import com.launchcircle.testers.core.model.ManagedCheckout
import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchDashboard
import com.launchcircle.testers.core.model.LaunchInvite
import com.launchcircle.testers.core.model.LaunchCircle
import com.launchcircle.testers.core.model.MissionFeedback
import com.launchcircle.testers.core.model.PilotConfig
import com.launchcircle.testers.core.model.TestMission
import com.launchcircle.testers.core.model.TestAssignment
import com.launchcircle.testers.core.model.managedCheckoutPriceLabel
import com.launchcircle.testers.core.model.TesterAssignment
import com.launchcircle.testers.core.model.parseCoreWorkflowSteps
import com.launchcircle.testers.core.model.UserProfile
import com.launchcircle.testers.R
import com.launchcircle.testers.feature.onboarding.AccountScreen
import com.launchcircle.testers.ui.theme.LaunchAttention
import java.util.Locale

@Composable
fun LaunchWorkspace(
    profile: UserProfile,
    viewModel: LaunchViewModel,
    deletionInProgress: Boolean,
    deletionError: String?,
    onDeleteAccount: () -> Unit,
    onLogout: () -> Unit,
    onSharedPool: () -> Unit = {},
    onViewMyGroup: (String) -> Unit = { onSharedPool() },
    guideStartSignal: Int = 0,
    communityHome: @Composable () -> Unit = {},
    homeBack: (() -> Unit)? = null,
) {
    val state by viewModel.state.collectAsState()
    val activity = LocalActivity.current
    LaunchedEffect(viewModel, profile.id) { viewModel.loadLaunches(profile.id) }
    val primaryDestination = state.pilotSurface == PilotSurface.NONE && state.destination in setOf(
        LaunchDestination.COMMUNITY_HOME,
        LaunchDestination.MY_LAUNCHES,
        LaunchDestination.DASHBOARD,
        LaunchDestination.TODAY_TESTS,
        LaunchDestination.TESTERS,
        LaunchDestination.ACCOUNT,
    )
    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        contentWindowInsets = WindowInsets.safeDrawing,
        topBar = {
            LaunchAppHeader(testerAccess = { TesterGroupAccessCard(state.testerGroupAccess, profile.login_email, state.loading, viewModel::updateTesterGroupAccess, viewModel::refreshTesterGroupAccess) }, onAccountAction = viewModel::showAccount, onGuideAction = { step -> if (step == 3) { if (state.capabilities.appGroupSelection) onSharedPool() } else viewModel.openGuideDestination(step, profile.login_email.equals("liuchanghu2018@gmail.com", ignoreCase = true)) }, guideAccountId = profile.id.toString(), guideStartSignal = guideStartSignal, onBack = if (state.destination == LaunchDestination.MY_LAUNCHES && state.pilotSurface == PilotSurface.NONE) homeBack else if (primaryDestination) null else ({
                if (state.pilotSurface == PilotSurface.GROUP_SETUP) viewModel.skipGroupSetup()
                else viewModel.back()
            }))
        },
        bottomBar = {
            if (primaryDestination) {
                LaunchNavigation(
                    destination = state.destination,
                    onHome = viewModel::showCommunityHome,
                    onTests = viewModel::showToday,
                    onMyLaunch = viewModel::showHome,
                    onCircle = onSharedPool,
                    showCircle = state.capabilities.appGroupSelection,
                )
            }
        },
    ) { contentPadding ->
        Column(Modifier.fillMaxSize().padding(contentPadding)) {
            if (state.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
            state.error?.let { ErrorBanner(it) }
            Box(Modifier.fillMaxSize()) {
                when (state.pilotSurface) {
                    PilotSurface.INVITE -> InviteScreen(
                        state.selectedApp, state.pilotConfig,
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
                            onSharedPool()
                        },
                        showCircle = state.capabilities.appGroupSelection,
                    )
                    PilotSurface.GROUP_SETUP -> state.selectedApp?.let {
                        GroupSetup(
                            it, state.pilotConfig, state.loading,
                            viewModel::confirmGoogleGroup, viewModel::skipGroupSetup,
                        )
                    }
                    PilotSurface.ADDITIONAL_APP_PAYMENT -> state.pendingPayment?.let { checkout ->
                        LaunchedEffect(activity, checkout.product_id) {
                            activity?.let { current -> viewModel.loadGooglePlayPrice(current, checkout.product_id) }
                        }
                        AdditionalAppPayment(
                            checkout = checkout,
                            actualPrice = state.googlePlayPrice,
                            loading = state.loading,
                            onCheckStatus = { activity?.let(viewModel::recoverAdditionalAppPurchase) },
                            onPurchase = { activity?.let(viewModel::launchAdditionalAppPurchase) },
                            onClose = viewModel::closeAdditionalAppPayment,
                        )
                    }
                    PilotSurface.MANAGED_PAYMENT -> state.pendingManagedPayment?.let { checkout ->
                        LaunchedEffect(activity, checkout.product_id, checkout.list_product_id) {
                            activity?.let { current ->
                                viewModel.loadGooglePlayPrice(current, checkout.product_id, checkout.list_product_id)
                            }
                        }
                        ManagedLaunchPayment(
                            checkout = checkout,
                            actualPrice = state.googlePlayPrice,
                            actualListPrice = state.googlePlayListPrice,
                            loading = state.loading,
                            onCheckStatus = viewModel::checkManagedPayment,
                            onPurchase = { activity?.let(viewModel::launchManagedPurchase) },
                            onClose = viewModel::closeManagedPayment,
                        )
                    }
                    PilotSurface.NONE -> when (state.destination) {
                        LaunchDestination.COMMUNITY_HOME -> communityHome()
                        LaunchDestination.MY_LAUNCHES -> communityHome()
                        LaunchDestination.ADD_APP -> AddApp(
                            viewModel::createApp,
                            viewModel::setDraftIcon,
                            loading = state.loading,
                            supportsOwnerAttestation = state.capabilities.ownerAttestation,
                        )
                        LaunchDestination.DASHBOARD -> {
                            val selected = state.selectedApp?.takeIf { it.owner_id == profile.id }
                                ?: state.launches.firstOrNull { it.owner_id == profile.id }
                            val dashboard = selected?.let { state.dashboards[it.id] }
                            if (selected != null && dashboard != null) {
                                Dashboard(
                                    selected, dashboard, state.launches.filter { it.owner_id == profile.id }, state.loading,
                                    viewModel::showDashboard,
                                    viewModel::showInvite, viewModel::matchTesters,
                                    viewModel::showTesters, viewModel::showFeedback,
                                    viewModel::showGoogleGroupSetup,
                                    viewModel::recordCoordinationTime,
                                    { trigger -> viewModel.recordManagedOfferViewed(selected.id, trigger) },
                                    { viewModel.startManagedCheckout(selected.id) },
                                    if (state.pilotConfig.cold_start_evidence_enabled) viewModel::showEvidence else null,
                                    viewModel::setAppIcon, { if (state.capabilities.appGroupSelection) onViewMyGroup(selected.id) },
                                    onAdd = if (profile.login_email.equals("liuchanghu2018@gmail.com", ignoreCase = true)) viewModel::showAddApp else null,
                                    onAttestOwnership = { viewModel.attestOwnership(selected.id) },
                                    supportsAppGroupSelection = state.capabilities.appGroupSelection,
                                )
                            } else if (!state.loading) {
                                Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(20.dp)) {
                                    Text(lcText("My Launch", "我的发布"), style = MaterialTheme.typography.headlineMedium)
                                    Text(lcText("Your app starts here", "从你的第一个 App 开始"), style = MaterialTheme.typography.titleLarge)
                                    Text(lcText("Add your app, set up test access, then join a matching group. You can manage everything here.", "添加 App、设置测试访问，再加入匹配的小组。应用的配置和管理都在这里完成。"))
                                    Button(onClick = viewModel::showAddApp, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(lcText("Add my app", "添加我的 App")) }
                                }
                            }
                        }
                        LaunchDestination.TODAY_TESTS -> Today(
                            state.todayAssignments, state.pilotConfig, viewModel::showAssignment,
                            access = state.testerGroupAccess,
                            accessCard = { TesterGroupAccessCard(state.testerGroupAccess, profile.login_email, state.loading, viewModel::updateTesterGroupAccess, viewModel::refreshTesterGroupAccess) },
                        )
                        LaunchDestination.ASSIGNMENT -> state.selectedAssignment?.let {
                            EvidenceAssignmentScreen(it, state.assignmentMissions, state.loading,
                                groupReady = state.testerGroupAccess?.ready == true,
                                sharedGroupUrl = state.pilotConfig.google_group_join_url,
                                accessCard = { TesterGroupAccessCard(state.testerGroupAccess, profile.login_email, state.loading, viewModel::updateTesterGroupAccess, viewModel::refreshTesterGroupAccess) },
                                viewModel::confirmAssignmentOptIn, viewModel::confirmAssignmentInstalled,
                                viewModel::showMission)
                        }
                        LaunchDestination.MISSION -> state.selectedMission?.let {
                            if (state.testerGroupAccess?.ready != true) {
                                Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp)) {
                                    TesterGroupAccessCard(state.testerGroupAccess, profile.login_email, state.loading, viewModel::updateTesterGroupAccess, viewModel::refreshTesterGroupAccess)
                                }
                            } else if (state.pilotConfig.cold_start_evidence_enabled) {
                                MissionEvidenceScreen(state.evidenceContext, state.loading,
                                    state.evidenceSavedId, viewModel::submitMissionEvidence,
                                    onHistory = viewModel::showMissionEvidenceHistory)
                            } else Mission(
                                it, viewModel::startMission, viewModel::confirmOptIn,
                                viewModel::confirmInstalled, viewModel::submitFeedback,
                                loading = state.loading, started = state.missionStarted,
                            )
                        }
                        LaunchDestination.TESTERS -> Testers(
                            app = state.selectedApp,
                            dashboard = state.selectedApp?.let { state.dashboards[it.id] },
                            rows = state.testers,
                            circle = state.circle,
                        )
                        LaunchDestination.EVIDENCE -> PublisherEvidenceScreen(
                            state.campaignEvidence, state.loading, state.evidenceNotice,
                            viewModel::refreshEvidence, viewModel::setEvidenceBuild,
                            viewModel::declareEvidenceFix, viewModel::showEvidenceDetail,
                            state.evidenceReportJson, viewModel::prepareEvidenceReport,
                        )
                        LaunchDestination.EVIDENCE_HISTORY -> EvidenceHistoryScreen(
                            state.evidenceRuns, viewModel::showEvidenceDetail)
                        LaunchDestination.EVIDENCE_DETAIL -> EvidenceRunDetailScreen(
                            state.evidenceDetail, state.loading, viewModel::beginEvidenceRetest)
                        LaunchDestination.EVIDENCE_RETEST -> EvidenceRetestScreen(
                            state.evidenceDetail, state.loading, state.evidenceSavedId,
                            viewModel::submitEvidenceRetest)
                        LaunchDestination.FEEDBACK -> Feedback(state.feedback)
                        LaunchDestination.ACCOUNT -> AccountScreen(
                            profile = profile,
                            deleting = deletionInProgress,
                            error = deletionError,
                            onBack = viewModel::back,
                            showBack = false,
                            onLogout = onLogout,
                            onDeleteAccount = onDeleteAccount,
                        )
                    }
                }
            }
        }
    }
}

@Composable
internal fun LaunchNavigation(
    destination: LaunchDestination,
    onHome: () -> Unit,
    onTests: () -> Unit,
    onMyLaunch: () -> Unit,
    onCircle: () -> Unit,
    showCircle: Boolean = true,
    circleSelected: Boolean = false,
) {
    data class Item(
        val label: String,
        val icon: androidx.compose.ui.graphics.vector.ImageVector,
        val selected: Boolean,
        val onClick: () -> Unit,
    )
    val items = buildList {
        add(
        Item(lcText("Home", "首页"), Icons.Rounded.Home, destination in setOf(LaunchDestination.COMMUNITY_HOME, LaunchDestination.MY_LAUNCHES), onHome),
        )
        if (showCircle) add(Item(lcText("Circle", "互测圈"), Icons.Rounded.Groups, circleSelected, onCircle))
        add(Item(lcText("Tests", "我的测试"), Icons.Rounded.Science, destination == LaunchDestination.TODAY_TESTS, onTests))
        add(Item(lcText("My Launch", "我的发布"), Icons.Rounded.RocketLaunch, destination == LaunchDestination.DASHBOARD, onMyLaunch))
    }
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
    onPool: () -> Unit,
 ) {
    val primaryApp = selectedApp ?: apps.firstOrNull()
    val dashboard = primaryApp?.let { dashboards[it.id] }
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp),
    ) {
        item {
            Text(stringResource(R.string.home), style = MaterialTheme.typography.headlineLarge)
            Text(stringResource(R.string.welcome_back, profile.display_name ?: stringResource(R.string.developer)), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        item { Button(onClick = onAdd, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.add_app)) } }
        item {
            OutlinedButton(onClick = onPool, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.public_pool_action)) }
            Text(stringResource(R.string.public_pool_help), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        items(apps, key = { "app-${it.id}" }) { app ->
            OutlinedButton(onClick = { onOpen(app) }, modifier = Modifier.fillMaxWidth()) {
                AppIcon(app.name, app.icon_url, app.package_name)
                Spacer(Modifier.width(12.dp))
                Text(app.name, modifier = Modifier.weight(1f))
            }
        }
        if (primaryApp == null || dashboard == null) {
            item {
                EmptyCard(
                    stringResource(R.string.first_launch_title),
                    stringResource(R.string.first_launch_body),
                )
            }
            item {
                MetricCard(
                    label = stringResource(R.string.todays_work),
                    value = stringResource(if (today.size == 1) R.string.test_count_singular else R.string.test_count_plural, today.size),
                    supporting = "~${today.sumOf { it.estimated_minutes }} min",
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        } else {
            item {
                CountdownHero(primaryApp, dashboard) { onOpen(primaryApp) }
            }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    MetricCard(
                        label = stringResource(R.string.tester_coverage),
                        value = "${dashboard.active_testers} / ${dashboard.google_minimum}",
                        supporting = if (dashboard.testers_needed_for_minimum == 0) stringResource(R.string.requirement_met) else
                            stringResource(R.string.more_testers_required, dashboard.testers_needed_for_minimum),
                        positive = dashboard.testers_needed_for_minimum == 0,
                        modifier = Modifier.weight(1f),
                    )
                    MetricCard(
                        label = stringResource(R.string.todays_work),
                        value = stringResource(if (today.size == 1) R.string.test_count_singular else R.string.test_count_plural, today.size),
                        supporting = "~${today.sumOf { it.estimated_minutes }} min",
                        modifier = Modifier.weight(1f),
                    )
                }
            }
            item {
                SectionHeader(stringResource(R.string.today), if (today.isNotEmpty()) stringResource(R.string.view_all) else null, onToday)
            }
            if (today.isEmpty()) {
                item { EmptyCard(stringResource(R.string.you_are_caught_up), stringResource(R.string.no_tests_today)) }
            } else {
                items(today, key = { "home-${it.id}" }) { mission ->
                    TodayAssignmentCard(assignment = mission, onClick = { onAssignment(mission) }, compact = true)
                }
            }
            item {
                SectionHeader(stringResource(R.string.circle_health))
                HealthCard(dashboard)
            }
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = onAccount, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.account_settings)) }
                TextButton(onClick = onLogout, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.sign_out)) }
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
                StatusBadge(stringResource(if (onTrack) R.string.testing_on_track else R.string.needs_attention), if (onTrack) StatusTone.SUCCESS else StatusTone.ATTENTION)
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
                    Text(stringResource(R.string.day_one_starts_after_requirement), style = MaterialTheme.typography.bodyLarge)
                } else if (dashboard.lifecycle_complete) {
                    Text(stringResource(R.string.internal_testing_complete), style = MaterialTheme.typography.headlineMedium)
                    Text(stringResource(R.string.production_app_can_be_prepared), style = MaterialTheme.typography.bodyLarge)
                } else {
                    Text(
                        dashboard.days_remaining.coerceAtLeast(0).toString(),
                        style = MaterialTheme.typography.displayLarge.copy(fontSize = 72.sp, lineHeight = 76.sp),
                    )
                    Text(stringResource(R.string.days_uppercase), style = MaterialTheme.typography.titleLarge)
                    Text(stringResource(R.string.until_internal_testing_eligibility), style = MaterialTheme.typography.bodyLarge)
                }
            }
            Text(
                if (dashboard.testing_started_at == null) {
                    stringResource(R.string.waiting_for_day_one)
                } else {
                    stringResource(R.string.day_of_total, dashboard.day.coerceAtLeast(0), totalDays)
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
                stringResource(R.string.testers_qualifying_count, dashboard.qualifying_tester_count, dashboard.required_tester_count),
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
                Text(stringResource(if (good) R.string.good else R.string.action_needed), style = MaterialTheme.typography.headlineSmall)
                StatusBadge(stringResource(if (good) R.string.healthy else R.string.attention), if (good) StatusTone.SUCCESS else StatusTone.ATTENTION)
            }
            Text(stringResource(R.string.active_testers_count, dashboard.active_testers), color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (dashboard.at_risk_testers > 0) {
                Text(stringResource(R.string.testers_need_attention_count, dashboard.at_risk_testers), color = LaunchAttention)
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
            if (app.developer_account_unlimited) {
                StatusBadge(stringResource(R.string.publisher_account_unlimited))
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.day_progress, dashboard?.day ?: 0, dashboard?.total_days ?: 14))
                Text(stringResource(R.string.active_count, dashboard?.active_testers ?: 0), color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            LinearProgressIndicator(
                progress = { (dashboard?.production_readiness ?: 0).coerceIn(0, 100) / 100f },
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun AdditionalAppPayment(
    checkout: AdditionalAppCheckout,
    actualPrice: String?,
    loading: Boolean,
    onCheckStatus: () -> Unit,
    onPurchase: () -> Unit,
    onClose: () -> Unit,
) {
    val isPaid = checkout.status == "PAID" || checkout.status == "CONSUMED"
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(stringResource(R.string.additional_app), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(
            when (checkout.status) {
                "PAID", "CONSUMED" -> stringResource(R.string.additional_app_purchase_confirmed)
                "FAILED", "EXPIRED" ->
                    stringResource(R.string.additional_app_purchase_cancelled)
                else ->
                    stringResource(R.string.additional_app_purchase_verification)
            },
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            actualPrice ?: stringResource(R.string.loading_google_play_price),
            style = MaterialTheme.typography.titleMedium,
        )
        Button(
            onClick = onPurchase,
            enabled = !loading && !isPaid && actualPrice != null,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.buy_with_google_play)) }
        Button(
            onClick = onCheckStatus,
            enabled = !loading,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(if (isPaid) R.string.apply_purchase else R.string.check_purchase_status)) }
        OutlinedButton(
            onClick = onClose,
            enabled = !loading,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.return_to_add_app)) }
    }
}

@Composable
private fun ManagedLaunchPayment(
    checkout: ManagedCheckout,
    actualPrice: String?,
    actualListPrice: String?,
    loading: Boolean,
    onCheckStatus: () -> Unit,
    onPurchase: () -> Unit,
    onClose: () -> Unit,
) {
    val isPaid = checkout.status == "PAID"
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(stringResource(R.string.managed_launch), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(
            when (checkout.status) {
                "PAID" -> stringResource(R.string.managed_purchase_confirmed)
                "FAILED", "EXPIRED" -> stringResource(R.string.managed_purchase_cancelled)
                else -> stringResource(R.string.managed_purchase_verification)
            },
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            managedCheckoutPriceLabel(
                actualListPrice,
                actualPrice,
                hasCredit = checkout.credit_amount > 0,
            ),
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.SemiBold,
        )
        Button(
            onClick = onPurchase,
            enabled = !loading && !isPaid && actualPrice != null,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.buy_with_google_play)) }
        Button(
            onClick = onCheckStatus,
            enabled = !loading,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(if (isPaid) R.string.refresh_confirmation else R.string.check_purchase_status)) }
        OutlinedButton(
            onClick = onClose,
            enabled = !loading,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.return_to_launch)) }
    }
}

@Composable
private fun AddApp(
    onCreate: (String, String, String, String?, String, List<String>, String, String?, Boolean) -> Unit,
    onDraftIcon: (String?) -> Unit,
    loading: Boolean = false,
    supportsOwnerAttestation: Boolean,
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    var playLink by rememberSaveable { mutableStateOf("") }
    var name by rememberSaveable { mutableStateOf("") }
    var workflowText by rememberSaveable { mutableStateOf("") }
    var draftIcon by androidx.compose.runtime.remember { mutableStateOf<String?>(null) }
    var ownershipAuthorized by rememberSaveable { mutableStateOf(false) }
    LaunchedEffect(Unit) { onDraftIcon(null) }
    val link = playLink.trim()
    val parsedPlayLink = com.launchcircle.testers.core.launch.PlayAppLink.parseClosedTestingLink(link)
    val steps = parseCoreWorkflowSteps(workflowText)
    val stepsTooLong = steps.any { it.length > 200 }
    val stepsInvalid = steps.size > 4 || stepsTooLong
    val valid = parsedPlayLink != null && name.isNotBlank() && draftIcon != null && steps.size >= 2 && !stepsInvalid &&
        (!supportsOwnerAttestation || ownershipAuthorized)
    val example = lcText("Open the app and try its main feature using sample data.\nCheck the result and report anything confusing.", "打开应用，用示例数据尝试主要功能。\n检查结果，反馈遇到的问题或不清楚的地方。")
    Column(Modifier.fillMaxSize()) {
        Column(Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(lcText("Add your app", "添加自己的 App"), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Surface(color = MaterialTheme.colorScheme.primaryContainer, shape = RoundedCornerShape(18.dp)) {
                Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Surface(color = MaterialTheme.colorScheme.primary, shape = CircleShape) {
                            Text("1", Modifier.padding(horizontal = 12.dp, vertical = 6.dp), color = MaterialTheme.colorScheme.onPrimary, fontWeight = FontWeight.Bold)
                        }
                    }
                    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(lcText("App details", "应用信息"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Text(lcText("App icon, Play link and name", "应用图标、Play 链接和名称"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            IconUpload(name.ifBlank { "App" }, draftIcon?.let { "data:image/png;base64,$it" }, enabled = !loading) { data ->
                draftIcon = data
                onDraftIcon(data)
            }
            Text(lcText("Closed testing link (required)", "封闭测试链接（必填）"), fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = playLink,
                onValueChange = { playLink = it },
                label = { Text(lcText("Google Play test link", "Google Play 测试链接")) },
                placeholder = { Text(stringResource(R.string.add_app_closed_testing_link_placeholder)) },
                supportingText = {
                    Text(
                        stringResource(
                            if (playLink.isNotBlank() && parsedPlayLink == null)
                                R.string.add_app_closed_testing_link_invalid
                            else R.string.add_app_closed_testing_link_help,
                        )
                    )
                },
                isError = playLink.isNotBlank() && parsedPlayLink == null,
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Uri),
                singleLine = true,
                enabled = !loading,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedButton(
                onClick = {
                    runCatching {
                        context.startActivity(Intent(Intent.ACTION_VIEW, android.net.Uri.parse("https://play.google.com/console")))
                    }
                },
                enabled = !loading,
            ) { Text(lcText("Open Play Console ↗", "打开 Play Console ↗")) }
            OutlinedTextField(name, { name = it }, label = { Text(lcText("App name (required)", "应用名称（必填）")) }, singleLine = true, enabled = !loading, modifier = Modifier.fillMaxWidth())
            Surface(color = MaterialTheme.colorScheme.primaryContainer, shape = RoundedCornerShape(16.dp)) {
                Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Surface(color = MaterialTheme.colorScheme.primary, shape = CircleShape) {
                        Text("2", Modifier.padding(horizontal = 12.dp, vertical = 6.dp), color = MaterialTheme.colorScheme.onPrimary, fontWeight = FontWeight.Bold)
                    }
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(lcText("Write test steps", "填写测试步骤"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Text(lcText("2–4 steps · one per line", "2–4 条测试步骤 · 每行一条"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    androidx.compose.material3.AssistChip(
                        onClick = { workflowText = if (workflowText.isBlank()) example else workflowText.trimEnd() + "\n" + example },
                        enabled = !loading && steps.size < 2,
                        label = { Text(lcText("Use starter steps", "使用示例步骤"), maxLines = 1) },
                    )
                }
            }
            OutlinedTextField(workflowText, { workflowText = it }, label = { Text(lcText("Test steps (required)", "测试步骤（必填）")) },
                isError = stepsInvalid,
                supportingText = {
                    val message = when {
                        steps.size > 4 -> lcText("Keep at most 4 test steps.", "最多填写 4 条测试步骤，请删减。")
                        stepsTooLong -> lcText("Shorten each step to 200 characters or fewer.", "每条测试步骤最多 200 字，请缩短。")
                        steps.isEmpty() -> lcText("Write 2 to 4 steps, one per line, or use the starter steps.", "请填写 2 到 4 条，每条另起一行，也可以使用示例步骤。")
                        steps.size == 1 -> lcText("Add at least 1 more step on a new line.", "还差至少 1 条，请另起一行填写。")
                        else -> lcText("Test steps complete (${steps.size})", "测试步骤已完成（${steps.size} 条）")
                    }
                    val color = when {
                        stepsInvalid -> MaterialTheme.colorScheme.error
                        steps.size < 2 -> MaterialTheme.colorScheme.primary
                        androidx.compose.foundation.isSystemInDarkTheme() -> androidx.compose.ui.graphics.Color(0xFF8DDBA4)
                        else -> androidx.compose.ui.graphics.Color(0xFF176C38)
                    }
                    Text(message, color = color, fontWeight = FontWeight.SemiBold)
                },
                minLines = 3, maxLines = 5, enabled = !loading, modifier = Modifier.fillMaxWidth())
            if (supportsOwnerAttestation) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Checkbox(checked = ownershipAuthorized, onCheckedChange = { ownershipAuthorized = it }, enabled = !loading)
                    Text(lcText(
                        "I own this app or am authorized to submit it for testing. Publisher identity is self-reported and may not be independently verified.",
                        "我拥有此应用，或已获授权提交测试。发布者身份由我自报，可能未经独立核验。",
                    ), style = MaterialTheme.typography.bodySmall)
                }
            } else {
                Text(
                    lcText("Ownership confirmation will be available after the service is updated. You can save this app now; it will remain pending until then.", "所有权确认将在服务端更新后可用。你现在可以保存此 App；在此之前它会保持待确认状态。"),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            Spacer(Modifier.height(8.dp))
        }
        Surface(tonalElevation = 3.dp) {
            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                if (!valid) Text(lcText(if (supportsOwnerAttestation) "To continue, add an app icon, a closed testing link, an app name, 2–4 test steps, and confirm submission authority." else "To continue, add an app icon, a closed testing link, an app name, and 2–4 test steps.", if (supportsOwnerAttestation) "继续前请添加应用图标、封闭测试链接、应用名称、2–4 条测试步骤，并确认提交权限。" else "继续前请添加应用图标、封闭测试链接、应用名称和 2–4 条测试步骤。"), style = MaterialTheme.typography.bodySmall)
                Button(onClick = {
                    val closedTestingLink = checkNotNull(parsedPlayLink)
                    onCreate(name.trim(), closedTestingLink.packageName, closedTestingLink.optInUrl, null, "LAUNCH_CIRCLE", steps, "", null, supportsOwnerAttestation && ownershipAuthorized)
                },
                    enabled = valid && !loading, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(lcText(if (loading) "Saving…" else "Save & set up test access", if (loading) "保存中…" else "保存并设置测试访问")) }
            }
        }
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
    val uri = LocalUriHandler.current
    var consoleOpenFailed by remember { mutableStateOf(false) }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(stringResource(R.string.connect_tester_access), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(app.name, color = MaterialTheme.colorScheme.primary)
        Text(
            lcText(
                "This is the one Launch Circle tester group. Add its email to every app's Play closed-test track. Testers join with the invite link once, then open each app's own Play test link.",
                "Launch Circle 统一使用这一个测试群组。发布者需将群组邮箱添加到每个 App 的 Play 封闭测试轨道。测试者通过邀请链接加入一次，再逐个打开各 App 的 Play 测试链接。",
            ),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Highlight {
            Text(lcText("Shared tester group email · for Play Console", "共用测试群组邮箱 · 用于 Play Console"), fontWeight = FontWeight.SemiBold)
            Text(config.google_group_email)
            Text(lcText("Copy this email into every Launch Circle app's closed-test track. The invite link below is for testers.", "请将此邮箱添加到每个 Launch Circle App 的封闭测试轨道。下方邀请链接供测试者使用。"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            OutlinedButton(onClick = { copy(context, config.google_group_email) }) { Text(lcText("Copy group email", "复制群组邮箱")) }
        }
        Text(lcText("Add this group to this app in Play Console", "在 Play Console 中为此 App 添加群组"), style = MaterialTheme.typography.titleMedium)
        OutlinedButton(
            onClick = { consoleOpenFailed = runCatching { uri.openUri("https://play.google.com/console") }.isFailure },
            modifier = Modifier.fillMaxWidth(),
        ) { Text(lcText("Open Google Play Console", "打开 Google Play Console")) }
        if (consoleOpenFailed) Text(lcText("Open play.google.com/console in your browser, then select this app.", "请在浏览器打开 play.google.com/console，然后选择此 App。"), color = MaterialTheme.colorScheme.error)
        listOf(
            stringResource(R.string.group_setup_step_open_console),
            stringResource(R.string.group_setup_step_closed_testing),
            stringResource(R.string.group_setup_step_manage_testers),
            stringResource(R.string.group_setup_step_add_group),
            stringResource(R.string.group_setup_step_enter_group, config.google_group_email),
            stringResource(R.string.group_setup_step_save),
            stringResource(R.string.group_setup_step_return_continue),
        ).forEach { Text(it) }
        AppTestInvitation(app, config)
        Text(
            lcText(
                "After saving the group in Play Console and publishing a closed-test release, confirm here. Launch Circle cannot check Play Console for you. A ready app will then appear on Home; internal App Groups are separate.",
                "在 Play Console 保存群组并开放封闭测试版本后，再回来确认。Launch Circle 无法替你读取 Play Console。App 满足上架条件后会显示在首页；内部互测小组是独立功能。",
            ),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            stringResource(R.string.play_console_user_confirmation_note),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Button(onClick = onConfirm, enabled = !loading && !app.google_group_configured, modifier = Modifier.fillMaxWidth()) {
            Text(if (app.google_group_configured) lcText("Tester access confirmed", "测试访问已确认") else lcText("I added the group to this app", "我已将群组添加到此 App"))
        }
        OutlinedButton(onClick = onLater, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.do_this_later)) }
    }
}

@Composable
private fun Dashboard(
    app: LaunchApp,
    data: LaunchDashboard,
    ownedApps: List<LaunchApp>,
    loading: Boolean,
    onSelectApp: (LaunchApp) -> Unit,
    onInvite: () -> Unit,
    onMatch: () -> Unit,
    onTesters: () -> Unit,
    onFeedback: () -> Unit,
    onGroupSetup: () -> Unit,
    onCoordinationTime: (Int, String) -> Unit,
    onManagedOfferViewed: (String) -> Unit,
    onManagedCheckout: () -> Unit,
    onEvidence: (() -> Unit)?,
    onIcon: (String, String?) -> Unit,
    onPool: () -> Unit,
    onAdd: (() -> Unit)? = null,
    onAttestOwnership: () -> Unit,
    supportsAppGroupSelection: Boolean,
) {
    var coordinationMinutesText by rememberSaveable(app.id) { mutableStateOf("") }
    var showPriorityOffer by rememberSaveable(app.id) { mutableStateOf(false) }
    LaunchedEffect(app.id, data.managed_offer_triggers.orEmpty()) {
        data.managed_offer_triggers.orEmpty().distinct().forEach(onManagedOfferViewed)
    }
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                androidx.compose.foundation.layout.Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(lcText("My Launch", "我的发布"), style = MaterialTheme.typography.headlineMedium)
                    if (onAdd != null) TextButton(onClick = onAdd, enabled = !loading) { Text(lcText("Add app", "添加 App")) }
                }
                if (ownedApps.size > 1) {
                    var appMenuOpen by rememberSaveable(app.id) { mutableStateOf(false) }
                    Box {
                        OutlinedButton(onClick = { appMenuOpen = true }, enabled = !loading, modifier = Modifier.fillMaxWidth()) {
                            Text(lcText("Managing: ", "正在管理：") + app.name + "  ▾", maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                        androidx.compose.material3.DropdownMenu(expanded = appMenuOpen, onDismissRequest = { appMenuOpen = false }) {
                            ownedApps.forEach { item ->
                                androidx.compose.material3.DropdownMenuItem(
                                    text = { Text(item.name, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                                    onClick = { appMenuOpen = false; onSelectApp(item) },
                                )
                            }
                        }
                    }
                } else {
                    Text(app.name, style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 2, overflow = TextOverflow.Ellipsis)
                }
            }
        }
        if (!supportsAppGroupSelection) item {
            Text(
                lcText("Owner confirmation and App Groups will be available after the service is updated.", "所有者确认和互测小组将在服务端更新后可用。"),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodySmall,
            )
        }
        if (supportsAppGroupSelection && !app.ownership_authorized) item {
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        lcText("PENDING_ATTESTATION · Owner confirmation needed", "PENDING_ATTESTATION · 待所有者确认"),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(lcText(
                        "This app was saved by an older client without an ownership statement. It cannot join a group or receive testers until you confirm that you own it or are authorized to submit it.",
                        "此 App 由旧版客户端保存，尚无所有权声明。确认你拥有该 App 或获准提交后，才能加入小组或招募测试者。",
                    ))
                    Button(onClick = onAttestOwnership, enabled = !loading, modifier = Modifier.fillMaxWidth()) {
                        Text(lcText("I own this app or am authorized to submit it", "我拥有此 App 或获准提交它"))
                    }
                }
            }
        }
        item {
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(lcText("Google Play tester access", "Google Play 测试访问"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    OutlinedButton(onClick = onInvite, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text(lcText("Share this app’s test invitation", "分享此 App 的测试邀请")) }
                    if (app.google_group_configured) {
                        Text(lcText("Confirmed. Your app is listed in Home. Internal App Groups are separate and optional.", "已确认。你的 App 已列入首页。Launch Circle 内部互测小组是独立的可选功能。"), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        if (supportsAppGroupSelection) Button(onClick = onPool, enabled = !loading, modifier = Modifier.fillMaxWidth()) {
                            Text(lcText("Browse App Groups", "浏览互测小组"))
                        }
                    } else {
                        Text(lcText("For this app, add the shared Launch Circle tester Google Group to its Play Console closed-test track, then come back and confirm.", "请为这个 App 在 Play Console 封闭测试轨道添加 Launch Circle 共用测试群组，然后回来确认。"), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Button(onClick = onGroupSetup, enabled = !loading, modifier = Modifier.fillMaxWidth()) {
                            Text(lcText("Set up tester access", "配置测试访问"))
                        }
                    }
                }
            }
        }
        if (onEvidence != null) item {
            OutlinedButton(onClick = onEvidence, enabled = !loading, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.publisher_evidence_title))
            }
        }
        item {
            Card(
                Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
            ) {
                Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(lcText("Testing progress", "测试进度"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Text(
                            if (data.testing_started_at == null) lcText("Waiting for tester activity", "等待测试者开始")
                            else stringResource(R.string.day_progress, data.day, data.total_days),
                            style = MaterialTheme.typography.headlineMedium,
                        )
                        if (data.testing_started_at != null) StatusBadge(localizedLabel(data.status))
                    }
                    LinearProgressIndicator(
                        progress = { data.production_readiness.coerceIn(0, 100) / 100f },
                        modifier = Modifier.fillMaxWidth().height(8.dp),
                        drawStopIndicator = {},
                    )
                    Text(
                        if (data.testing_started_at == null) {
                            stringResource(R.string.testers_ready_count, data.qualifying_tester_count, data.required_tester_count)
                        } else if (data.lifecycle_complete) {
                            stringResource(R.string.fourteen_day_test_complete)
                        } else {
                            stringResource(R.string.days_remaining, data.days_remaining.coerceAtLeast(0))
                        },
                        style = MaterialTheme.typography.titleMedium,
                    )
                    if (data.estimated_ready_date.isNotBlank()) {
                        Text(stringResource(R.string.estimated_production_date, data.estimated_ready_date), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    if (data.replacement_status != "NONE") {
                        Text(
                            when (data.replacement_status) {
                                "COVERAGE_RESTORED" -> stringResource(R.string.coverage_restored)
                                "REPLACEMENT_ASSIGNED" -> stringResource(R.string.replacement_assigned)
                                else -> stringResource(R.string.coverage_at_risk)
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
            SectionHeader(stringResource(R.string.milestones))
            MilestoneTimeline(data)
        }
        item {
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(stringResource(R.string.activity), style = MaterialTheme.typography.titleMedium)
                    Text(stringResource(R.string.missions_progress, data.missions_completed, data.missions_total_available))
                    Text(stringResource(R.string.feedback_response_count, data.feedback_count))
                    TextButton(onClick = onFeedback, enabled = !loading && data.feedback_count > 0) { Text(stringResource(R.string.view_feedback)) }
                }
            }
        }
        item {
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(stringResource(R.string.workload), style = MaterialTheme.typography.titleMedium)
                    Text(stringResource(R.string.tester_time_reported, data.tester_minutes_reported))
                    Text(stringResource(R.string.developer_coordination_time, data.developer_coordination_minutes, data.coordination_entries))
                    if (data.remaining_reciprocal_missions > 0) {
                        Text(stringResource(R.string.remaining_circle_missions, data.remaining_reciprocal_missions, data.remaining_reciprocal_minutes))
                    }
                    OutlinedTextField(
                        value = coordinationMinutesText,
                        onValueChange = { coordinationMinutesText = it.filter(Char::isDigit).take(3) },
                        label = { Text(stringResource(R.string.coordination_time_minutes)) },
                        supportingText = { Text(stringResource(R.string.log_coordination_time_help)) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    val minutes = coordinationMinutesText.toIntOrNull()
                    Button(
                        onClick = {
                            onCoordinationTime(checkNotNull(minutes), "COORDINATION")
                            coordinationMinutesText = ""
                        },
                        enabled = !loading && minutes != null && minutes in 1..480,
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text(stringResource(R.string.log_coordination_time)) }
                }
            }
        }
        if (data.managed_launch_purchased) {
            item {
                OutlinedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(stringResource(R.string.managed_launch), style = MaterialTheme.typography.titleMedium)
                        Text(stringResource(R.string.managed_launch_active))
                    }
                }
            }
        }
        item {
            var editIcon by rememberSaveable(app.id) { mutableStateOf(false) }
            OutlinedButton(onClick = { editIcon = !editIcon }, enabled = !loading) { Text(if (editIcon) "Close icon editor" else "Update app icon") }
            if (editIcon) AppIconEditor(app, loading, onIcon)
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
private fun InviteScreen(app: LaunchApp?, config: PilotConfig, onClose: () -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        TextButton(onClick = onClose) { Text(lcText("Back", "返回")) }
        if (app == null) Text(lcText("Select your app in My Launch first.", "请先在我的发布选择自己的 App。"))
        else AppTestInvitation(app, config)
    }
}

@Composable
private fun AppTestInvitation(app: LaunchApp, config: PilotConfig) {
    val context = LocalContext.current
    val uri = LocalUriHandler.current
    var help by rememberSaveable(app.id) { mutableStateOf(false) }
    var openFailed by remember { mutableStateOf(false) }
    val invitation = lcText(
        "Please test " + app.name + "\n\nJoin this app's Google Play test:\n" + app.opt_in_url + "\n\nFirst time testing with Launch Circle? Join our shared Google Group once:\n" + config.google_group_join_url + "\n\nUse the same Google account for the group, Play test and Play Store. Then install, try the app and send feedback.",
        "邀请你测试 " + app.name + "\n\n加入此 App 的 Google Play 测试：\n" + app.opt_in_url + "\n\n首次参与 Launch Circle 测试？先加入共用 Google 群组一次：\n" + config.google_group_join_url + "\n\n群组、Play 测试和 Play 商店请使用同一个 Google 账号。然后安装、使用并提交反馈。",
    )
    Highlight {
        Text(lcText("Invite testers for ", "邀请测试：") + app.name, style = MaterialTheme.typography.titleMedium)
        Text(app.opt_in_url, style = MaterialTheme.typography.bodySmall)
        Button(onClick = { share(context, invitation, app.name) }, modifier = Modifier.fillMaxWidth()) { Text(lcText("Share this app's test invitation", "分享此 App 的测试邀请")) }
        OutlinedButton(onClick = { copy(context, invitation) }, modifier = Modifier.fillMaxWidth()) { Text(lcText("Copy test invitation", "复制测试邀请")) }
        OutlinedButton(onClick = { openFailed = runCatching { uri.openUri(app.opt_in_url) }.isFailure }, modifier = Modifier.fillMaxWidth()) { Text(lcText("Open this app's Play test", "打开此 App 的 Play 测试页面")) }
        if (openFailed) Text(lcText("Copy the invitation and open its Play link in your browser.", "请复制邀请，并在浏览器打开其中的 Play 链接。"), color = MaterialTheme.colorScheme.error)
        TextButton(onClick = { help = !help }) { Text(lcText("First-time tester help", "首次测试者帮助")) }
        if (help) {
            Text(lcText("Join the shared Google Group once, then use this app's Play link above. Existing members can go straight to the Play link.", "首次加入共用 Google 群组后，再打开上方此 App 的 Play 链接。已有成员可以直接打开 Play 链接。"))
            OutlinedButton(onClick = { openFailed = runCatching { uri.openUri(config.google_group_join_url) }.isFailure }) { Text(lcText("Join the shared Google Group", "加入共用 Google 群组")) }
        }
    }
}

@Composable
private fun JoinScreen(loading: Boolean, onJoin: (String) -> Unit, onClose: () -> Unit) {
    var code by rememberSaveable { mutableStateOf("") }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(stringResource(R.string.join_launch_circle), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(stringResource(R.string.enter_shared_invite_code))
        OutlinedTextField(
            code, { code = it.uppercase().take(8) },
            label = { Text(stringResource(R.string.invite_code)) }, placeholder = { Text(stringResource(R.string.invite_code_example)) },
            modifier = Modifier.fillMaxWidth(),
        )
        Button(onClick = { onJoin(code) }, enabled = !loading && code.isNotBlank(), modifier = Modifier.fillMaxWidth()) {
            Text(stringResource(R.string.join_launch_circle))
        }
        OutlinedButton(onClick = onClose, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.cancel)) }
    }
}

@Composable
private fun JoinSuccess(
    config: PilotConfig,
    onAdd: () -> Unit,
    onTests: () -> Unit,
    onCircle: () -> Unit,
    showCircle: Boolean = true,
    circleSelected: Boolean = false,
) {
    val uri = LocalUriHandler.current
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(stringResource(R.string.you_are_in), style = MaterialTheme.typography.displaySmall, fontWeight = FontWeight.Bold)
        Text(stringResource(R.string.next_steps), style = MaterialTheme.typography.titleLarge)
        Text(stringResource(R.string.join_launch_circle_group_step))
        Text(stringResource(R.string.add_android_app_step))
        Text(stringResource(R.string.help_test_developers_step))
        Text(
            lcText(
                "Group membership alone does not enroll you in any specific Play closed test.",
                "加入群组本身不会让你自动加入任何一个 App 的 Play 闭测。",
            ),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Button(onClick = { uri.openUri(config.google_group_join_url) }, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.join_google_group)) }
        OutlinedButton(onClick = onAdd, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.add_my_app)) }
        OutlinedButton(onClick = onTests, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.view_test_apps)) }
        if (showCircle) OutlinedButton(onClick = onCircle, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.view_circle_members)) }
    }
}

@Composable
private fun Today(
    assignments: List<TestAssignment>,
    config: PilotConfig,
    onAssignment: (TestAssignment) -> Unit,
    access: com.launchcircle.testers.core.model.TesterGroupAccess?,
    accessCard: @Composable () -> Unit,
) {
    val uri = LocalUriHandler.current
    val completed = assignments.filter { it.status == "COMPLETED" || it.completed_at != null || it.feedback_submitted }
    val toDo = assignments.filterNot { it.status == "COMPLETED" || it.completed_at != null || it.feedback_submitted }
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text(stringResource(R.string.tests), style = MaterialTheme.typography.headlineLarge)
            Text(stringResource(R.string.todays_tests), style = MaterialTheme.typography.titleLarge, modifier = Modifier.padding(top = 4.dp))
            Text(lcText("Set up once, then follow each app’s test steps.", "完成一次测试访问设置，再按每个 App 的步骤操作。"), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        item { accessCard() }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                MetricCard(lcText("To do", "待测试"), toDo.size.toString(), lcText("Assigned apps", "分配的应用"), modifier = Modifier.weight(1f))
                MetricCard(lcText("Done", "已完成"), completed.size.toString(), lcText("Saved feedback", "已保存反馈"), modifier = Modifier.weight(1f))
            }
        }
        if (assignments.isEmpty()) item { EmptyCard(lcText("You’re ready for the next task", "等待下一项测试任务"), lcText("No tests are assigned today. Browse App Groups to see your group and its apps.", "今天没有分配的测试。可前往 App Groups 查看自己的小组和应用。")) }
        if (toDo.isNotEmpty()) item { SectionHeader(stringResource(R.string.to_do)) }
        items(toDo, key = { "todo-${it.id}" }) { assignment ->
            TodayAssignmentCard(assignment, { onAssignment(assignment) })
        }
        if (completed.isNotEmpty()) item { SectionHeader(stringResource(R.string.completed)) }
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
                        stringResource(R.string.mission_type_test, localizedLabel(mission.mission_type)),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(stringResource(R.string.estimated_minutes_short, mission.estimated_minutes), style = MaterialTheme.typography.labelLarge)
                    if (compact && !completed) {
                        Button(onClick = onClick, modifier = Modifier.defaultMinSize(minHeight = 48.dp)) { Text(stringResource(R.string.start)) }
                    } else if (!completed) {
                        FilledTonalButton(onClick = onClick, modifier = Modifier.defaultMinSize(minHeight = 48.dp)) {
                            Text(stringResource(if (inProgress) R.string.continue_ else R.string.start_test))
                        }
                    }
                }
            }
            if (completed) Text(if (mission.feedback_submitted) "Feedback submitted" else stringResource(R.string.completed), style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.tertiary)
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
                AppIcon(assignment.app_name, assignment.icon_url, assignment.package_name)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(
                        assignment.app_name,
                        style = MaterialTheme.typography.titleMedium,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        color = if (completed) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurface,
                    )
                    Text(stringResource(R.string.mission_type_test, localizedLabel(assignment.test_type)), color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text(stringResource(R.string.estimated_minutes_short, assignment.estimated_minutes), style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (completed) Text(if (assignment.feedback_submitted) lcText("Feedback submitted", "反馈已提交") else stringResource(R.string.completed), style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.tertiary)
                else {
                    val label = stringResource(if (compact) R.string.start else R.string.start_test)
                    FilledTonalButton(onClick = onClick, modifier = Modifier.defaultMinSize(minHeight = 48.dp)) { Text(label) }
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
        Text(stringResource(R.string.mission_type_test_title, localizedLabel(assignment.test_type)), style = MaterialTheme.typography.titleLarge)
        Text(stringResource(R.string.about_minutes, assignment.estimated_minutes))
        Text(stringResource(R.string.assigned_for_day, assignment.assignment_day), color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (assignment.status == "COMPLETED" || assignment.completed_at != null) {
            Highlight { Text(stringResource(R.string.completed), fontWeight = FontWeight.SemiBold); Text(stringResource(R.string.completion_saved)) }
        } else {
            Button(onClick = { uri.openUri(assignment.opt_in_url) }, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.start_test))
            }
            Button(onClick = onComplete, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.mark_test_complete)) }
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
    onSubmit: (String, String?, String?, Int?) -> Unit,
    loading: Boolean = false,
    started: Boolean = false,
) {
    val initial = when (mission.assignment_status) {
        "ACTIVE", "COMPLETED", "INSTALLED" -> 3
        "OPTED_IN" -> 2
        else -> 0
    }
    var playOpened by rememberSaveable(mission.id) { mutableStateOf(false) }
    val step = if (started) 4 else if (initial == 0 && playOpened) 1 else initial
    var completionResult by rememberSaveable(mission.id) { mutableStateOf<String?>(null) }
    var timeSpentText by rememberSaveable(mission.id) { mutableStateOf("") }
    var issue by rememberSaveable(mission.id) { mutableStateOf("") }
    var suggestion by rememberSaveable(mission.id) { mutableStateOf("") }
    val missionSteps = mission.steps.orEmpty().ifEmpty { listOf(missionPrompt(mission.mission_type)) }
    val missionGoal = mission.goal.orEmpty().ifBlank { missionPrompt(mission.mission_type) }
    val uri = LocalUriHandler.current
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(mission.app_name, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(stringResource(R.string.mission_type_test_title, localizedLabel(mission.mission_type)), style = MaterialTheme.typography.titleLarge)
        Text(stringResource(R.string.about_minutes, mission.estimated_minutes))
        if (step == 0) Button(onClick = { uri.openUri(mission.opt_in_url); playOpened = true }, enabled = !loading && !mission.feedback_submitted, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.open_play_testing_link)) }
        if (step == 1) Button(onClick = { onOptIn() }, enabled = !loading && !mission.feedback_submitted, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.confirm_opt_in)) }
        if (step == 2) Button(onClick = { onInstalled() }, enabled = !loading && !mission.feedback_submitted, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.confirm_installed)) }
        if (step == 3) {
            Highlight {
                Text(stringResource(R.string.your_mission), fontWeight = FontWeight.SemiBold)
                Text(missionGoal)
                missionSteps.forEachIndexed { index, instruction ->
                    Text("${index + 1}. $instruction")
                }
            }
            Button(onClick = { onStart() }, enabled = !loading && !mission.feedback_submitted, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.start_mission)) }
        }
        if (step >= 4) {
            Text(stringResource(R.string.mission_result_question), fontWeight = FontWeight.SemiBold)
            Option(
                completionResult == "COMPLETED",
                stringResource(R.string.result_completed),
                stringResource(R.string.result_completed_help),
            ) { completionResult = "COMPLETED" }
            Option(
                completionResult == "COMPLETED_WITH_DIFFICULTY",
                stringResource(R.string.result_with_difficulty),
                stringResource(R.string.result_with_difficulty_help),
            ) { completionResult = "COMPLETED_WITH_DIFFICULTY" }
            Option(
                completionResult == "COULD_NOT_COMPLETE",
                stringResource(R.string.result_could_not_complete),
                stringResource(R.string.result_could_not_complete_help),
            ) { completionResult = "COULD_NOT_COMPLETE" }
            OutlinedTextField(
                value = timeSpentText,
                onValueChange = { timeSpentText = it.filter(Char::isDigit).take(3) },
                label = { Text(stringResource(R.string.time_taken_prompt)) },
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(issue, { issue = it }, label = { Text(stringResource(R.string.what_happened_optional)) }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(suggestion, { suggestion = it }, label = { Text(stringResource(R.string.suggestion_optional)) }, modifier = Modifier.fillMaxWidth())
            val timeSpentMinutes = timeSpentText.toIntOrNull()
            Button(
                onClick = { onSubmit(checkNotNull(completionResult), issue, suggestion, checkNotNull(timeSpentMinutes)) },
                enabled = !loading && !mission.feedback_submitted && completionResult != null && timeSpentMinutes != null && timeSpentMinutes in 1..240,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.submit_feedback)) }
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
    val attentionRows = rows.filter { participationState(it) == "AT_RISK" }
    val criticalRows = rows.filter { participationState(it) == "CRITICAL" }
    val droppedRows = rows.filter { participationState(it) == "DROPPED" }
    val activeRows = rows.filter { participationState(it) == "ACTIVE" }
    val active = dashboard?.active_testers ?: activeRows.size
    val attention = dashboard?.at_risk_testers ?: attentionRows.size + criticalRows.size
    val healthy = dashboard?.status != "AT_RISK" && dashboard?.circle_health == "GOOD"
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text(stringResource(R.string.circle), style = MaterialTheme.typography.headlineLarge)
            Text(
                app?.let { stringResource(R.string.app_testing_circle, it.name) } ?: stringResource(R.string.testing_circle),
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
                            Text(stringResource(R.string.circle_health_title), style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(stringResource(if (healthy) R.string.healthy else R.string.needs_attention), style = MaterialTheme.typography.headlineSmall)
                        }
                        StatusBadge(stringResource(if (healthy) R.string.on_track else R.string.attention), if (healthy) StatusTone.SUCCESS else StatusTone.ATTENTION)
                    }
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(stringResource(R.string.tester_coverage_title), style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
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
                        CircleMetric(active.toString(), stringResource(R.string.active), StatusTone.SUCCESS, Modifier.weight(1f))
                        CircleMetric(attention.toString(), stringResource(R.string.attention), StatusTone.ATTENTION, Modifier.weight(1f))
                        CircleMetric(droppedRows.size.toString(), stringResource(R.string.dropped), StatusTone.NEUTRAL, Modifier.weight(1f))
                    }
                }
            }
        }
        if (app != null) {
            item {
                SectionHeader(stringResource(R.string.app_status))
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
                        StatusBadge(localizedLabel(dashboard?.status ?: app.status))
                    }
                }
            }
        }
        circle?.let { launchCircle ->
            item {
                SectionHeader(stringResource(R.string.circle_members))
                Text(
                    stringResource(R.string.active_members_count, launchCircle.active_member_count, launchCircle.max_members),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            items(launchCircle.members, key = { "circle-${it.id}" }) { member ->
                OutlinedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(member.member_label, style = MaterialTheme.typography.titleMedium)
                        Text(
                            stringResource(
                                when {
                                    member.role == "OWNER" -> R.string.circle_owner
                                    member.status == "ACTIVE" -> R.string.active_member
                                    else -> R.string.circle_member_status
                                },
                                member.status.lowercase().replaceFirstChar { it.uppercase() },
                            ),
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
        if (rows.isEmpty()) item { EmptyCard(stringResource(R.string.no_tester_statuses), stringResource(R.string.tester_statuses_explanation)) }
        if (attentionRows.isNotEmpty()) item { SectionHeader(stringResource(R.string.at_risk)) }
        items(attentionRows, key = { "attention-${it.id}" }) { tester ->
            TesterStatusRow(tester)
        }
        if (activeRows.isNotEmpty()) item { SectionHeader(stringResource(R.string.active_members)) }
        items(activeRows, key = { "active-${it.id}" }) { tester ->
            TesterStatusRow(tester)
        }
        if (criticalRows.isNotEmpty()) item { SectionHeader(stringResource(R.string.critical)) }
        items(criticalRows, key = { "critical-${it.id}" }) { tester ->
            TesterStatusRow(tester, muted = true)
        }
        if (droppedRows.isNotEmpty()) item { SectionHeader(stringResource(R.string.dropped)) }
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
    tester.health_status in setOf("CRITICAL", "INACTIVE") -> "CRITICAL"
    tester.health_status == "AT_RISK" -> "AT_RISK"
    tester.participation_state == "NEEDS_ATTENTION" -> "AT_RISK"
    tester.participation_state == "INACTIVE" -> "CRITICAL"
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
                Text(stringResource(R.string.day_number, tester.testing_day), color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (tester.total_missions > 0) {
                    Text(stringResource(R.string.completed_mission_count, tester.completed_missions, tester.total_missions), color = MaterialTheme.colorScheme.onSurfaceVariant)
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
        item { Text(stringResource(R.string.feedback), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold) }
        if (rows.isEmpty()) item { EmptyCard(stringResource(R.string.no_feedback_yet), stringResource(R.string.feedback_after_missions)) }
        items(rows, key = { it.id }) { row ->
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(row.tester_label + " · " + localizedLabel(row.mission_type), fontWeight = FontWeight.SemiBold)
                    row.completion_result?.let { Text(stringResource(R.string.feedback_result, localizedLabel(it))) }
                    row.time_spent_minutes?.let { Text(stringResource(R.string.feedback_tester_time, it)) }
                    row.issue_text?.let { Text(stringResource(R.string.feedback_issue, it)) }
                    row.suggestion_text?.let { Text(stringResource(R.string.feedback_suggestion, it)) }
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

@Composable
private fun testerLabel(value: TesterAssignment): String = stringResource(
    when {
        participationState(value) == "DROPPED" -> R.string.dropped
        participationState(value) == "CRITICAL" -> R.string.critical
        participationState(value) == "AT_RISK" -> R.string.at_risk
        value.is_replacement -> R.string.replacement
        value.health_status == "NEW" -> R.string.new_tester
        value.health_status == "HEALTHY" -> R.string.healthy
        else -> R.string.active
    },
)

private fun testerTone(value: TesterAssignment): StatusTone = when {
    participationState(value) in setOf("ACTIVE", "HEALTHY") -> StatusTone.SUCCESS
    participationState(value) in setOf("AT_RISK", "CRITICAL") -> StatusTone.ATTENTION
    else -> StatusTone.NEUTRAL
}

@Composable
private fun missionPrompt(type: String): String = stringResource(
    when (type) {
        "INSTALL_FIRST_IMPRESSION" -> R.string.mission_prompt_first_impression
        "CORE_FEATURE" -> R.string.mission_prompt_core_feature
        "EDGE_CASE" -> R.string.mission_prompt_edge_case
        "SECOND_USE" -> R.string.mission_prompt_second_use
        "RETEST" -> R.string.mission_prompt_retest
        "FINAL_FEEDBACK" -> R.string.mission_prompt_final_feedback
        else -> R.string.mission_prompt_generic
    },
)

@Composable
private fun localizedLabel(value: String): String = stringResource(
    when (value) {
        "WAITING_FOR_TESTERS" -> R.string.waiting_for_testers
        "TESTING" -> R.string.testing_status
        "AT_RISK", "COVERAGE_AT_RISK" -> R.string.coverage_at_risk
        "TESTING_COMPLETE" -> R.string.fourteen_day_test_complete
        "PRODUCTION_READY" -> R.string.production_ready_status
        "DRAFT" -> R.string.draft_status
        "INSTALL_FIRST_IMPRESSION" -> R.string.mission_first_impression
        "CORE_FEATURE" -> R.string.mission_core_feature
        "EDGE_CASE" -> R.string.mission_edge_case
        "SECOND_USE" -> R.string.mission_second_use
        "RETEST" -> R.string.mission_retest
        "FINAL_FEEDBACK" -> R.string.mission_final_feedback
        "COMPLETED" -> R.string.result_completed
        "COMPLETED_WITH_DIFFICULTY" -> R.string.result_with_difficulty
        "COULD_NOT_COMPLETE" -> R.string.result_could_not_complete
        "PRIORITY" -> R.string.priority_support
        else -> return pretty(value)
    },
)

private fun pretty(value: String): String =
    value.lowercase().split("_").joinToString(" ") { it.replaceFirstChar(Char::uppercase) }

private fun copy(context: Context, value: String) {
    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    clipboard.setPrimaryClip(ClipData.newPlainText("Launch Circle", value))
}

private fun share(context: Context, value: String, message: String = "Join my Android testing circle") {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_TEXT, message + "\n\n" + value)
    }
    context.startActivity(Intent.createChooser(intent, "Share invite"))
}


@Composable
private fun AppIconEditor(app: LaunchApp, loading: Boolean, onIcon: (String, String?) -> Unit) {
    IconUpload(app.name, app.icon_url, app.package_name, enabled = !loading) { onIcon(app.id, it) }
    TextButton(onClick = { onIcon(app.id, null) }) { Text(lcText("Get icon from Google Play", "从 Google Play 获取图标")) }
}

@Composable
internal fun IconUpload(name: String, url: String?, packageName: String? = null, enabled: Boolean = true, onUpload: (String) -> Unit) {
    val context = LocalContext.current
    var error by androidx.compose.runtime.remember { mutableStateOf<String?>(null) }
    val picker = androidx.activity.compose.rememberLauncherForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri != null) {
            runCatching {
                val bytes = context.contentResolver.openInputStream(uri)?.use { it.readIconBytes() }
                    ?: error("Cannot read this image")
                require(bytes.size <= 1048576) { "Choose an image smaller than 1 MB" }
                require((bytes.size >= 8 && bytes.copyOfRange(0, 8).contentEquals(byteArrayOf(0x89.toByte(), 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a))) ||
                    (bytes.size >= 3 && bytes[0] == 0xff.toByte() && bytes[1] == 0xd8.toByte() && bytes[2] == 0xff.toByte())) {
                    "Choose a PNG or JPEG image"
                }
                require(android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size) != null) { "Choose a PNG or JPEG image" }
                onUpload(android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP))
            }.onSuccess { error = null }.onFailure { error = it.message ?: "Cannot read this image" }
        }
    }
    OutlinedCard(Modifier.fillMaxWidth()) {
        androidx.compose.foundation.layout.Row(
            Modifier.fillMaxWidth().padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            AppIcon(name, url, packageName)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(
                    if (url.isNullOrBlank()) lcText("App icon required", "需要应用图标") else lcText("App icon added", "已添加应用图标"),
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(lcText("Choose a PNG or JPEG image · up to 1 MB", "选择 PNG 或 JPEG 图片 · 最大 1 MB"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            androidx.compose.material3.FilledTonalButton(onClick = { picker.launch("image/*") }, enabled = enabled) {
                Text(if (url.isNullOrBlank()) lcText("Choose", "选择图标") else lcText("Change", "更换"))
            }
        }
    }
    error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
}

@Composable
internal fun AppIcon(name: String, url: String?, packageName: String? = null) {
    if (packageName == "com.launchcircle.testers") {
        androidx.compose.foundation.Image(
            painter = androidx.compose.ui.res.painterResource(com.launchcircle.testers.R.drawable.launch_circle_logo),
            contentDescription = name,
            modifier = Modifier.size(48.dp),
        )
        return
    }
    val context = LocalContext.current
    var bitmap by androidx.compose.runtime.remember(url, packageName) { mutableStateOf<android.graphics.Bitmap?>(null) }
    LaunchedEffect(url, packageName) {
        bitmap = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
            runCatching {
                if (packageName == "com.regevidencehub.cablecert") {
                    val icon = context.packageManager.getApplicationIcon(packageName)
                    return@runCatching icon.toBitmap()
                }
                val value = url ?: return@runCatching null
                val bytes = if (value.startsWith("data:image/")) android.util.Base64.decode(value.substringAfter(","), android.util.Base64.DEFAULT) else {
                    val connection = java.net.URL(value).openConnection().apply { connectTimeout = 5000; readTimeout = 5000 }
                    connection.getInputStream().use { it.readIconBytes() }
                }
                if (bytes.size > 1048576) null else android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            }.getOrNull()
        }
    }
    val loaded = bitmap
    if (loaded != null) androidx.compose.foundation.Image(loaded.asImageBitmap(), contentDescription = name, modifier = Modifier.size(48.dp))
    else Box(Modifier.size(48.dp), contentAlignment = Alignment.Center) { Text(name.take(1).uppercase()) }
}

private fun java.io.InputStream.readIconBytes(): ByteArray {
    val output = java.io.ByteArrayOutputStream()
    val buffer = ByteArray(8192)
    while (output.size() <= 1048576) {
        val count = read(buffer, 0, minOf(buffer.size, 1048577 - output.size()))
        if (count < 0) break
        output.write(buffer, 0, count)
    }
    return output.toByteArray()
}
