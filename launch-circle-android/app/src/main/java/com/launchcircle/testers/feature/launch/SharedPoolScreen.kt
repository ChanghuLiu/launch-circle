package com.launchcircle.testers.feature.launch

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.Groups
import androidx.compose.material.icons.rounded.School
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Icon
import androidx.compose.material3.TextButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.core.model.*
import com.launchcircle.testers.core.network.ApiFactory
import com.launchcircle.testers.core.storage.TokenStore
import kotlinx.coroutines.launch
import retrofit2.HttpException

private class PoolClient(
    val tokens: TokenStore,
    val refresh: suspend () -> Boolean,
) {
    suspend fun <T> call(block: suspend (String) -> T): T {
        val access = tokens.accessToken ?: run {
            if (!refresh()) error("Could not refresh session")
            tokens.accessToken ?: error("Could not refresh session")
        }
        val auth = "Bearer $access"
        return try { block(auth) } catch (error: HttpException) {
            if (error.code() != 401 || !refresh()) throw error
            block("Bearer " + (tokens.accessToken ?: error("Could not refresh session")))
        }
    }
}

@Composable
fun SharedPoolScreen(
    baseUrl: String, tokens: TokenStore, refresh: suspend () -> Boolean,
    home: Boolean = false, ownerAppId: String? = null, onAdd: () -> Unit = {}, onTests: () -> Unit = {}, onLaunch: () -> Unit = {},
    onBackChange: ((() -> Unit)?) -> Unit = {},
    onSessionExpired: () -> Unit = {},
) {
    val api = remember(baseUrl) { ApiFactory.create(baseUrl) }
    val client = remember(tokens) { PoolClient(tokens, refresh) }
    val scope = rememberCoroutineScope()
    var groups by remember { mutableStateOf(emptyList<AppTestGroup>()) }
    var ownerOptions by remember { mutableStateOf<OwnerAppGroups?>(null) }
    var joinTarget by remember { mutableStateOf<OwnerAppGroupOption?>(null) }
    var consentChecked by rememberSaveable { mutableStateOf(false) }
    var selectedGroupId by rememberSaveable { mutableStateOf<String?>(null) }
    LaunchedEffect(selectedGroupId) { onBackChange(if (selectedGroupId == null) null else ({ selectedGroupId = null })) }
    DisposableEffect(Unit) { onDispose { onBackChange(null) } }
    androidx.activity.compose.BackHandler(enabled = selectedGroupId != null) { selectedGroupId = null }
    var supplies by remember { mutableStateOf(emptyList<PoolSupply>()) }
    var ownedCount by remember { mutableStateOf(0) }
    var admin by remember { mutableStateOf(false) }
    var loaded by remember { mutableStateOf(false) }
    var leaveTarget by remember { mutableStateOf<String?>(null) }
    var rulesExpanded by rememberSaveable { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var sessionExpired by remember { mutableStateOf(false) }
    var notice by remember { mutableStateOf<String?>(null) }
    suspend fun load() {
        val profile = client.call { api.me(it) }
        admin = profile.login_email.equals("liuchanghu2018@gmail.com", ignoreCase = true)
        val owned = client.call { api.apps(it) }.filter { it.owner_id == profile.id }
        ownedCount = owned.size
        groups = client.call { api.appGroups(it) }.sortedByDescending { it.my_group }
        ownerOptions = ownerAppId?.let { appId -> client.call { api.ownerAppGroups(it, appId) } }
        if (!home) supplies = owned.map { app -> client.call { api.poolSupply(it, app.id) } }
        loaded = true
    }
    fun action(block: suspend () -> Unit) {
        if (busy) return
        busy = true; error = null; sessionExpired = false
        scope.launch {
            try { block(); load() }
            catch (failure: Exception) {
                if (failure is kotlinx.coroutines.CancellationException) throw failure
                val authFailure = failure is HttpException && failure.code() == 401
                sessionExpired = tokens.refreshToken == null
                if (authFailure && sessionExpired) onSessionExpired()
                error = when {
                    authFailure && sessionExpired -> "Session expired. Sign in again."
                    authFailure -> "Could not refresh your session. Check the connection and try again."
                    failure is HttpException && failure.code() == 409 -> {
                        val detail = runCatching { org.json.JSONObject(failure.response()?.errorBody()?.string().orEmpty()).optString("detail") }.getOrDefault("")
                        when (detail) {
                            "APP_GROUP_FULL", "APP_GROUP_CLOSED" -> "所选组已满或关闭，请重新选择。"
                            "APP_SETUP_INCOMPLETE" -> "请先完成 App 详情和测试访问配置。"
                            "APP_ADMIN_REVIEW_REQUIRED" -> "此 App 需要管理员审核，请联系支持。"
                            "APP_ALREADY_IN_ANOTHER_GROUP", "OWNER_ALREADY_IN_ANOTHER_APP_GROUP", "OWNER_ALREADY_HAS_APP_IN_GROUP" -> "此账号或 App 已属于其他组，不能自动移动；请查看 App Groups 或联系管理员处理例外。"
                            else -> "无法加入此组，请刷新选组列表后重试。"
                        }
                    }
                    failure is HttpException && failure.code() == 404 -> "This app is no longer available. Refresh the list."
                    failure is HttpException -> "Unable to update. Please retry."
                    tokens.refreshToken == null -> {
                        sessionExpired = true
                        onSessionExpired()
                        "Session expired. Sign in again."
                    }
                    else -> "Unable to connect. Please retry."
                }
            } finally { busy = false }
        }
    }
    LaunchedEffect(selectedGroupId, ownerAppId) { action {} }
    joinTarget?.let { target ->
        AlertDialog(
            onDismissRequest = { if (!busy) { joinTarget = null; consentChecked = false } },
            title = { Text(lcText("Confirm mutual testing", "确认同意互测")) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(lcText(
                        if (target.already_selected && !target.owner_joined) "Your app is already in ${target.name}. Join with your account and confirm mutual-testing consent? Your own app will never be assigned to you."
                        else "Add ${ownerOptions?.app_name.orEmpty()} and your account to ${target.name}? You agree to test other group members’ apps and submit real feedback. Your own app will never be assigned to you.",
                        if (target.already_selected && !target.owner_joined) "你的 App 已在 ${target.name}。现在将你的账号加入并确认同意互测？系统不会把你自己的 App 分配给你。"
                        else "将 ${ownerOptions?.app_name.orEmpty()} 和你的账号加入 ${target.name}？你同意测试组内其他成员的 App 并提交真实反馈。系统不会把你自己的 App 分配给你。",
                    ))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = consentChecked, onCheckedChange = { consentChecked = it }, enabled = !busy)
                        Text(lcText("I agree to mutual testing", "我同意参加互测"))
                    }
                }
            },
            confirmButton = {
                Button(enabled = consentChecked && !busy, onClick = {
                    val selected = target
                    joinTarget = null
                    consentChecked = false
                    action {
                        val result = client.call { api.joinOwnerAppGroup(it, ownerAppId!!, selected.id, AppGroupConsent(consent = true)) }
                        notice = if (result.qualified_tester_count == 0) "已入组，等待合格测试者；入组不会开始计天。" else "已加入 ${selected.name}，当前有 ${result.qualified_tester_count} 位合格测试者。"
                    }
                }) { Text(lcText("Confirm and join", "确认并入组")) }
            },
            dismissButton = { TextButton(enabled = !busy, onClick = { joinTarget = null; consentChecked = false }) { Text(lcText("Cancel", "取消")) } },
        )
    }
    leaveTarget?.let { groupId ->
        AlertDialog(onDismissRequest = { if (!busy) leaveTarget = null },
            title = { Text(lcText("Leave App Group?", "退出互测小组？")) },
            text = { Text(lcText("Reciprocal tasks in this group will stop. Feedback and history are kept. The group reopens the slot for another developer. Google Play opt-in is managed separately.", "本组相关互测任务会停止，席位释放给其他开发者。已有反馈和历史保留。Google Play 的加入状态需要另行管理。")) },
            confirmButton = { TextButton(enabled = !busy, onClick = {
                leaveTarget = null
                action { client.call { api.leaveAppGroup(it, groupId) }; selectedGroupId = null; notice = "You left the group. View My Launch when ready." }
            }) { Text(lcText("Leave group", "确认退出")) } },
            dismissButton = { TextButton(enabled = !busy, onClick = { leaveTarget = null }) { Text(lcText("Stay in group", "留在小组")) } })
    }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item {
            Text(lcText(if (ownerAppId != null) "Choose an App Group" else if (home) "App Groups" else "My launch", if (ownerAppId != null) "选择互测小组" else if (home) "互测小组" else "我的发布"), style = MaterialTheme.typography.headlineMedium)
            Text(lcText(if (ownerAppId != null) "Choose an open group for this configured app. The server checks ownership, readiness and capacity again when you confirm." else if (home) "Browse groups and join the group that contains your app." else "You decide whether to join an App Group for mutual testing.", if (ownerAppId != null) "为已配置的 App 选择一个开放小组。确认时服务端会重新核对所有权、配置和名额。" else if (home) "浏览小组，并加入包含你 App 的小组。" else "是否加入互测小组由你决定。"))
            if (home) {
                Text(lcText("Automatic matching · 15 app slots · join your matched group", "系统自动建组与匹配 · 15 个 App 席位 · 加入自己的匹配小组"), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
                TextButton(onClick = { rulesExpanded = !rulesExpanded }) { Text(lcText(if (rulesExpanded) "Hide group rules" else "How groups work", if (rulesExpanded) "收起规则" else "小组如何运作")) }
                if (rulesExpanded) OutlinedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(lcText("Created automatically", "系统自动建组"), style = MaterialTheme.typography.titleMedium)
                        Text(lcText("Complete app details and Play access to appear on Home. The administrator opens recruitment and matches your app; you decide whether to join the matched group.", "完成应用资料和 Play 访问配置后自动显示在首页。管理员开启招募并匹配小组，你再自主决定是否加入。"))
                        Text(lcText("15 app slots · one app per developer", "15 个 App 席位 · 每位开发者一个 App"), style = MaterialTheme.typography.titleMedium)
                        Text(lcText("Full groups close to new apps. Join your matched group to accept its current and future test tasks. You never test your own app: 15 slots provide at most 14 peers, not 12 verified Play testers.", "满 15 个席位后停止接收新 App。加入自己的匹配小组后，接受当前和后续成员的互测任务。自己不测试自己的 App，因此满组最多只有 14 位互测伙伴，不等于 12 名有效 Play 测试者。"))
                        Text(lcText("Pause, leave and return", "暂停、退出与重新参加"), style = MaterialTheme.typography.titleMedium)
                        Text(lcText("The administrator can pause recruitment. Leaving stops unfinished mutual tasks and frees your group slot; feedback stays. Returning requires a new group match and your consent.", "管理员可以暂停招募。退出会停止未完成的互测并释放小组席位，反馈保留。重新参加需要重新匹配小组，并由你确认加入。"))
                        Text(lcText("Google Group membership and each app’s Play enrollment are separate. Existing larger groups keep their members but receive no new apps while full.", "Google 群组成员身份与每个 App 的 Play 加入操作需要另行完成。已有超出新上限的小组保留成员，满员期间不接收新 App。"), style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            notice?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
            if (error != null && !sessionExpired) TextButton(onClick = { action {} }, enabled = !busy) { Text(lcText("Try again", "重试")) }
            if (home && loaded && ownedCount > 0 && groups.none { it.my_group }) {
                Text(lcText("Your app has no matched group yet. Complete setup in My Launch; the administrator manages recruitment.", "你的 App 尚未匹配小组。请在我的发布完成配置；招募由管理员管理。"))
                OutlinedButton(onClick = onLaunch, enabled = !busy) { Text(lcText("Open My Launch", "打开我的发布")) }
            }
        }
        if (ownerAppId != null) {
            val options = ownerOptions
            if (options == null && loaded) item { Text(lcText("No App Group options are available yet.", "目前没有可选的小组。")) }
            options?.let { owner ->
                item { Text(owner.app_name, style = MaterialTheme.typography.titleLarge) }
                items(owner.groups, key = { "owner-${it.id}" }) { group ->
                    OutlinedCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(group.name, style = MaterialTheme.typography.titleLarge)
                            Text("${group.remaining_app_slots} 个 App 名额剩余 · ${group.test_required_app_count} 个需测试 App · ${group.member_count} 位互测成员")
                            if (group.exempt_app_count > 0) Text("免测 App：${group.exempt_app_count} 个")
                            Text(when {
                                group.owner_joined -> "此 App 和账号已入组"
                                group.already_selected -> "App 已入组；账号尚未同意互测"
                                group.status == "CLOSED" -> "小组已关闭"
                                group.status == "FULL" -> "小组已满"
                                else -> "开放中"
                            })
                            Button(enabled = group.can_select && !group.owner_joined && !busy, onClick = { joinTarget = group }) {
                                Text(when {
                                    group.owner_joined -> "已入组"
                                    group.already_selected -> "确认加入此组"
                                    else -> "选择此组"
                                })
                            }
                        }
                    }
                }
                if (owner.groups.any { it.owner_joined }) {
                    val progress = owner.app_progress
                    item {
                        OutlinedCard(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text("此 App 的测试进度", style = MaterialTheme.typography.titleMedium)
                                if (progress.no_test_required) {
                                    Text("此 App 已设为免测，不参与测试周期。")
                                } else {
                                    Text("合格测试者：${progress.qualified_tester_count} / ${progress.required_tester_count}")
                                    if (progress.testing_started_at == null) {
                                        Text("尚未开始计天 · 第 ${progress.day} / ${progress.total_days} 天")
                                        Text("入组和组满不会启动计天；达到合格测试者门槛后才开始。", color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    } else {
                                        Text("已开始 · 第 ${progress.day} / ${progress.total_days} 天")
                                        Text("开始时间：${progress.testing_started_at}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } else if (home) {
            val selected = groups.firstOrNull { it.id == selectedGroupId }
            if (selected == null) {
                if (loaded && groups.isEmpty()) item { Text(lcText("No groups yet. Set up your app in My Launch to get started.", "暂时没有小组。请先到“我的发布”添加并设置你的 App。")) }
                items(groups, key = { it.id }) { group ->
                    OutlinedCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(lcText(group.name, group.name.removeSuffix(" Group") + " 互测小组"), style = MaterialTheme.typography.titleLarge)
                            Text(lcText(if (group.my_group) "Your testing group" else "Preview only · matched members can join", if (group.my_group) "你的互测小组" else "仅供浏览 · 匹配到本组才能加入"))
                            Text(lcText("${group.occupied_slots} / ${group.capacity} app slots · ${group.test_required_app_count} apps need testing · ${group.member_count} mutual testers", "${group.occupied_slots} / ${group.capacity} 个席位 · ${group.test_required_app_count} 个需测试 App · ${group.member_count} 位互测成员 · " + when (group.status) { "FORMING" -> "接收新应用"; "FULL" -> "已满"; else -> "已关闭" }))
                            if (group.exempt_app_count > 0) Text("免测 App：${group.exempt_app_count} 个")
                            Button(enabled = !busy, onClick = { selectedGroupId = group.id }) { Text(lcText(if (group.joined) "Open my group" else "Explore apps", if (group.joined) "打开我的小组" else "查看应用")) }
                            group.apps.forEach { app ->
                                androidx.compose.foundation.layout.Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                    AppIcon(app.name, app.icon_url)
                                    Column(Modifier.weight(1f)) {
                                        Text(app.name)
                                        Text(if (app.no_test_required) "免测 App" else "需测试", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                                    }
                                }
                            }
                        }
                    }
                }
            } else {
                item {
                    Text(lcText(selected.name, selected.name.removeSuffix(" Group") + " 互测小组"), style = MaterialTheme.typography.headlineMedium)
                    Text(lcText("Joining agrees to test this group’s current and future apps, up to 14 other developers, and send real feedback. Play enrollment and installation are separate actions. A forming group does not yet provide 12 testers.", "加入后，你同意测试本组当前及后续加入的其他 App，并提交真实反馈，最多 14 个。Google Play 加入和安装仍需逐个完成。组建中的小组不代表已有 12 位有效测试者。"))
                    when {
                        selected.joined -> {
                            Button(onClick = {}, enabled = false) { Text(lcText("Group joined", "已加入小组")) }
                            OutlinedButton(enabled = !busy, onClick = onTests) { Text(lcText("Open my group tests", "打开我的测试")) }
                        }
                        selected.my_group && !selected.ready_to_join -> OutlinedButton(onClick = onLaunch, enabled = !busy) { Text(lcText("View My Launch", "查看我的发布")) }
                        selected.my_group -> Button(enabled = !busy, onClick = {
                            action {
                                client.call { api.joinAppGroup(it, selected.id) }
                                notice = "Group joined. Open Tests to complete each app's Play opt-in and installation."
                                onTests()
                            }
                        }) { Text(lcText("Join group and test its apps", "加入小组并互测")) }
                        ownedCount == 0 -> Button(enabled = !busy && loaded, onClick = onLaunch) { Text(lcText("Set up my app in My Launch", "去我的发布设置 App")) }
                        else -> Text(lcText("Your app belongs to its automatically matched group. Open that group to join.", "你的 App 已自动匹配到其他小组，请打开自己的小组参加互测。"))
                    }
                }
                item {
                    if (selected.my_group || selected.joined) OutlinedButton(enabled = !busy, onClick = { leaveTarget = selected.id }) { Text(lcText("Leave this group", "退出这个小组")) }
                }
                items(selected.apps, key = { it.app_id }) { app ->
                    OutlinedCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            AppIcon(app.name, app.icon_url)
                            Text(app.name, style = MaterialTheme.typography.titleLarge)
                            if (app.owned) Text(lcText("Your app", "我的 App"))
                            Text(if (app.no_test_required) "免测 App" else "需测试", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                            app.workflow_steps.forEachIndexed { index, step -> Text("${index + 1}. $step") }
                        }
                    }
                }
            }
        } else {
            items(supplies, key = { it.app_id }) { supply ->
                OutlinedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(supply.name, style = MaterialTheme.typography.titleLarge)
                        Text(when {
                            !supply.ready_to_list -> "Setup needed: confirm Google Group, Play test link and test steps in My Launch."
                            supply.listed -> "Recruiting in the community"
                            else -> "Recruitment not open"
                        })
                        Text("Reported joined and installed: ${supply.reported_joined_and_installed} / 12")
                        Text("Verify Google Play eligibility in your Play Console.")
                        Text(lcText("Recruitment is managed by the administrator. You choose whether to join your App Group.", "招募由管理员管理；是否加入内部互测小组由你决定。"))
                    }
                }
            }
        }
    }
}


@Composable
private fun CommunityActionTile(
    modifier: Modifier,
    title: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    primary: Boolean,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    val colors = MaterialTheme.colorScheme
    Card(
        enabled = enabled,
        onClick = onClick,
        modifier = modifier.heightIn(min = 88.dp),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (primary) colors.primary else colors.surfaceContainerLow,
            contentColor = if (primary) colors.onPrimary else colors.onSurface,
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = if (primary) 3.dp else 0.dp),
    ) {
        Column(
            Modifier.fillMaxWidth().padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Surface(
                color = if (primary) colors.onPrimary.copy(alpha = 0.16f) else colors.primaryContainer,
                shape = RoundedCornerShape(12.dp),
            ) {
                Icon(
                    icon,
                    contentDescription = title,
                    tint = if (primary) colors.onPrimary else colors.primary,
                    modifier = Modifier.padding(7.dp).size(22.dp),
                )
            }
            Text(title, style = MaterialTheme.typography.titleSmall)
        }
    }
}

class CommunityAppsCache {
    var apps by mutableStateOf(emptyList<PoolOpportunity>())
    var busy by mutableStateOf(false)
    var error by mutableStateOf<String?>(null)
    var notice by mutableStateOf<String?>(null)
    var loaded by mutableStateOf(false)
    var sessionExpired by mutableStateOf(false)
    var loadJob: kotlinx.coroutines.Job? = null
}

@Composable
fun CommunityAppsScreen(
    baseUrl: String, tokens: TokenStore, refresh: suspend () -> Boolean,
    onAdd: () -> Unit, onTests: () -> Unit, onLaunch: () -> Unit, onGroup: () -> Unit,
    showGroups: Boolean = true,
    groupsResolved: Boolean = true,
    groupsCheckFailed: Boolean = false,
    onRetryCapabilities: () -> Unit = {},
    onSessionExpired: () -> Unit = {}, onBeginnerGuide: () -> Unit = {},
    requestScope: kotlinx.coroutines.CoroutineScope,
    cache: CommunityAppsCache = remember { CommunityAppsCache() },
) {
    val api = remember(baseUrl) { ApiFactory.create(baseUrl) }
    val client = remember(tokens) { PoolClient(tokens, refresh) }
    val scope = rememberCoroutineScope()
    suspend fun load() {
        cache.busy = true; cache.error = null; cache.sessionExpired = false
        try {
            cache.apps = client.call { api.communityApps(it) }
            cache.loaded = true
        } catch (failure: Exception) {
            if (failure is kotlinx.coroutines.CancellationException) throw failure
            val authFailure = failure is HttpException && failure.code() == 401
            cache.sessionExpired = tokens.refreshToken == null
            if (cache.sessionExpired) onSessionExpired()
            cache.error = when {
                cache.sessionExpired -> "Session expired. Sign in again."
                authFailure -> "Could not refresh your session. Check the connection and try again."
                else -> "Unable to connect. Please retry."
            }
        } finally { cache.busy = false }
    }
    fun requestLoad(force: Boolean = false) {
        if (com.launchcircle.testers.BuildConfig.USE_DEMO_REPOSITORY) {
            cache.apps = emptyList()
            cache.error = null
            cache.sessionExpired = false
            cache.loaded = true
            cache.busy = false
            return
        }
        if (cache.busy || cache.loadJob?.isActive == true || (!force && cache.loaded)) return
        cache.loadJob = requestScope.launch { load() }
    }
    fun refresh() { requestLoad(force = true) }
    LaunchedEffect(cache) { requestLoad() }
    androidx.compose.foundation.lazy.LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.primary,
                shape = RoundedCornerShape(22.dp),
            ) {
                Column(
                    Modifier.fillMaxWidth().padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Surface(
                            color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.16f),
                            shape = RoundedCornerShape(14.dp),
                        ) {
                            Icon(
                                Icons.Rounded.School,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onPrimary,
                                modifier = Modifier.padding(10.dp).size(24.dp),
                            )
                        }
                        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(
                                lcText("Getting started", "新手指南"),
                                style = MaterialTheme.typography.labelLarge,
                                color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.82f),
                            )
                            Text(
                                lcText("New to Launch Circle?", "刚开始使用 Launch Circle？"),
                                style = MaterialTheme.typography.headlineSmall,
                                color = MaterialTheme.colorScheme.onPrimary,
                            )
                        }
                    }
                    Button(
                        onClick = onBeginnerGuide,
                        colors = androidx.compose.material3.ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.onPrimary,
                            contentColor = MaterialTheme.colorScheme.primary,
                        ),
                        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                    ) { Text(lcText("Start the beginner guide", "开始新手指南")) }
                }
            }
            Text(lcText("All apps", "所有 App"), style = MaterialTheme.typography.headlineLarge)
            Text(
                if (cache.loaded) lcText(
                    "${cache.apps.size} apps listed. Scroll to browse. Apps with complete details and Play access appear here.",
                    "当前列出 ${cache.apps.size} 个 App，向下滚动可浏览。应用资料和 Play 测试访问配置完成后，即可显示在这里。",
                ) else lcText(
                    "Browse all registered apps.",
                    "应用资料和 Play 测试访问配置完成后，即可显示在这里。",
                ),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (com.launchcircle.testers.BuildConfig.USE_DEMO_REPOSITORY) {
                Text(
                    lcText("Demo build: live community listings are disabled.", "演示版本：真实社区列表已停用。"),
                    color = MaterialTheme.colorScheme.tertiary,
                )
            }
            if (cache.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            cache.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            cache.notice?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
            if (cache.error != null && !cache.sessionExpired) TextButton(onClick = { refresh() }) { Text(lcText("Try again", "重试")) }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                if (showGroups) CommunityActionTile(
                    modifier = Modifier.weight(1f),
                    title = lcText("Add my app", "添加我的 App"),
                    icon = Icons.Rounded.Add,
                    primary = true,
                    onClick = onAdd,
                )
                CommunityActionTile(
                    modifier = Modifier.weight(1f),
                    title = lcText("App Groups", "互测小组"),
                    icon = Icons.Rounded.Groups,
                    primary = false,
                    enabled = groupsResolved && showGroups,
                    onClick = onGroup,
                )
            }
            if (!groupsResolved && groupsCheckFailed) {
                Text(
                    lcText("Unable to check App Groups support. Check your connection and retry.", "暂时无法检查互测小组支持。请检查网络后重试。"),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                TextButton(onClick = onRetryCapabilities) { Text(lcText("Try again", "重试")) }
            } else if (!groupsResolved) LinearProgressIndicator(Modifier.fillMaxWidth())
            if (groupsResolved && !showGroups) Text(
                lcText("App Groups will be available after the service is updated.", "互测小组将在服务端更新后可用。"),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (cache.loaded && cache.apps.isEmpty()) Text(lcText("No apps have been registered yet.", "目前尚未登记 App。"))
        }
        items(cache.apps, key = { "community-${it.app_id}" }) { app ->
            OutlinedCard(Modifier.fillMaxWidth()) {
                Row(
                    Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                ) {
                    AppIcon(app.name, app.icon_url)
                    Text(
                        app.name,
                        modifier = Modifier.weight(1f),
                        style = MaterialTheme.typography.titleSmall,
                        maxLines = 1,
                        overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis,
                    )
                    when {
                        app.owned -> Text(lcText("Your app", "我的 App"), style = MaterialTheme.typography.labelMedium)
                        app.joined -> Text(lcText("Joined", "已加入"), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
                        app.available -> TextButton(
                            enabled = !cache.busy,
                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
                            onClick = {
                                scope.launch {
                                    cache.busy = true; cache.error = null
                                    try {
                                        client.call { api.acceptPoolApp(it, app.app_id) }
                                        cache.notice = "Joined ${app.name}. Open Tests for the next steps."
                                        load()
                                    } catch (failure: Exception) {
                                        if (failure is kotlinx.coroutines.CancellationException) throw failure
                                        cache.error = "Unable to join this app. Refresh and try again."
                                    } finally { cache.busy = false }
                                }
                            },
                        ) { Text(lcText("Join", "加入")) }
                        else -> Text(lcText("Unavailable", "暂不可加入"), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
    }
}
