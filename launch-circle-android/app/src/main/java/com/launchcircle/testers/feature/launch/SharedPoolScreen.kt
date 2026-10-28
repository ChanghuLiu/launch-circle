package com.launchcircle.testers.feature.launch

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.TextButton
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
        val auth = "Bearer " + (tokens.accessToken ?: error("Sign in again"))
        return try { block(auth) } catch (error: HttpException) {
            if (error.code() != 401 || !refresh()) throw error
            block("Bearer " + (tokens.accessToken ?: error("Sign in again")))
        }
    }
}

@Composable
fun SharedPoolScreen(
    baseUrl: String, tokens: TokenStore, refresh: suspend () -> Boolean,
    home: Boolean = false, onAdd: () -> Unit = {}, onTests: () -> Unit = {}, onLaunch: () -> Unit = {},
    onBackChange: ((() -> Unit)?) -> Unit = {},
) {
    val api = remember(baseUrl) { ApiFactory.create(baseUrl) }
    val client = remember(tokens) { PoolClient(tokens, refresh) }
    val scope = rememberCoroutineScope()
    var groups by remember { mutableStateOf(emptyList<AppTestGroup>()) }
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
    var notice by remember { mutableStateOf<String?>(null) }
    suspend fun load() {
        val profile = client.call { api.me(it) }
        admin = profile.login_email.equals("liuchanghu2018@gmail.com", ignoreCase = true)
        val owned = client.call { api.apps(it) }.filter { it.owner_id == profile.id }
        ownedCount = owned.size
        groups = client.call { api.appGroups(it) }.sortedByDescending { it.my_group }
        if (!home) supplies = owned.map { app -> client.call { api.poolSupply(it, app.id) } }
        loaded = true
    }
    fun action(block: suspend () -> Unit) {
        if (busy) return
        busy = true; error = null
        scope.launch {
            try { block(); load() }
            catch (failure: Exception) {
                if (failure is kotlinx.coroutines.CancellationException) throw failure
                error = when (failure) {
                    is HttpException -> when (failure.code()) {
                        401 -> "Session expired. Sign in again."
                        409 -> "Unable to join this group. Check that your app is configured and matched here, or open the group you already joined."
                        404 -> "This app is no longer available. Refresh the list."
                        else -> "Unable to update. Please retry."
                    }
                    else -> "Unable to connect. Please retry."
                }
            } finally { busy = false }
        }
    }
    LaunchedEffect(selectedGroupId) { action {} }
    val lifecycleOwner = androidx.lifecycle.compose.LocalLifecycleOwner.current
    val refreshOnResume by rememberUpdatedState(newValue = { action {} })
    DisposableEffect(lifecycleOwner) {
        val observer = androidx.lifecycle.LifecycleEventObserver { _, event ->
            if (event == androidx.lifecycle.Lifecycle.Event.ON_RESUME) refreshOnResume()
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    leaveTarget?.let { groupId ->
        AlertDialog(onDismissRequest = { if (!busy) leaveTarget = null },
            title = { Text(lcText("Leave App Group?", "退出互测小组？")) },
            text = { Text(lcText("Your app's recruitment will pause and reciprocal tasks in this group will stop. Feedback and history are kept. The group reopens the slot for another developer. Google Play opt-in is managed separately.", "你的 App 将暂停招募，本组相关互测任务会停止，席位释放给其他开发者。已有反馈和历史保留。Google Play 的加入状态需要另行管理。")) },
            confirmButton = { TextButton(enabled = !busy, onClick = {
                leaveTarget = null
                action { client.call { api.leaveAppGroup(it, groupId) }; selectedGroupId = null; notice = "You left the group. Resume recruitment in My Launch when ready." }
            }) { Text(lcText("Leave group", "确认退出")) } },
            dismissButton = { TextButton(enabled = !busy, onClick = { leaveTarget = null }) { Text(lcText("Stay in group", "留在小组")) } })
    }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item {
            Text(lcText(if (home) "App Groups" else "My launch", if (home) "互测小组" else "我的发布"), style = MaterialTheme.typography.headlineMedium)
            Text(lcText(if (home) "Discover apps and test together." else "Pause or resume recruitment here. Pausing keeps your group slot and existing tasks; use Leave group to stop mutual testing and release the slot.", if (home) "发现应用，和开发者一起互测。" else "在这里暂停或恢复招募。暂停保留席位和任务；退出小组才会停止互测并释放席位。"))
            if (home) {
                TextButton(onClick = { rulesExpanded = !rulesExpanded }) { Text(lcText(if (rulesExpanded) "Hide group rules" else "How groups work", if (rulesExpanded) "收起规则" else "小组如何运作")) }
                if (rulesExpanded) Text("15 developers maximum · 1 app per developer · test up to 14 other apps. Full groups stop receiving new apps. Leaving releases your slot and pauses your app; history stays. Pausing recruitment keeps your slot; leaving releases it. New developers are matched into open slots. App Groups organize mutual testing; Google Groups provide Play test access. App slots do not prove active testers or Google eligibility.")
            }
            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            notice?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
            if (error != null) TextButton(onClick = { action {} }, enabled = !busy) { Text(lcText("Try again", "重试")) }
            if (home && loaded && ownedCount > 0 && groups.none { it.my_group }) {
                Text(lcText("Your app is not recruiting in a group. Finish setup or resume recruitment in My Launch.", "你的 App 尚未在小组招募，请到“我的发布”完成设置或恢复招募。"))
                OutlinedButton(onClick = onLaunch, enabled = !busy) { Text(lcText("Open My Launch", "打开我的发布")) }
            }
        }
        if (home) {
            val selected = groups.firstOrNull { it.id == selectedGroupId }
            if (selected == null) {
                if (loaded && groups.isEmpty()) item { Text(lcText("No groups yet. Set up your app in My Launch to get started.", "暂时没有小组。请先到“我的发布”添加并设置你的 App。")) }
                items(groups, key = { it.id }) { group ->
                    OutlinedCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(lcText(group.name, group.name.removeSuffix(" Group") + " 互测小组"), style = MaterialTheme.typography.titleLarge)
                            Text(lcText(if (group.my_group) "Your testing group" else "Discover this group’s apps", if (group.my_group) "你的互测小组" else "看看小组里有哪些应用"))
                            Text(lcText("${group.occupied_slots} / ${group.capacity} app slots · " + if (group.status == "FORMING") "Accepting apps" else "Full", "${group.occupied_slots} / ${group.capacity} 个席位 · " + if (group.status == "FORMING") "接收新应用" else "已满"))
                            Button(enabled = !busy, onClick = { selectedGroupId = group.id }) { Text(lcText(if (group.joined) "Open my group" else "Explore apps", if (group.joined) "打开我的小组" else "查看应用")) }
                            group.apps.forEach { app ->
                                androidx.compose.foundation.layout.Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                    AppIcon(app.name, app.icon_url)
                                    Text(app.name, modifier = Modifier.weight(1f))
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
                        selected.my_group && !selected.ready_to_join -> OutlinedButton(onClick = onLaunch, enabled = !busy) { Text(lcText("Resume recruitment in My Launch", "去我的发布恢复招募")) }
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
                            else -> "Recruitment paused"
                        })
                        Text("Reported joined and installed: ${supply.reported_joined_and_installed} / 12")
                        Text("Verify Google Play eligibility in your Play Console.")
                        Button(enabled = !busy && (supply.listed || supply.ready_to_list), onClick = {
                            action { client.call { api.setPoolListing(it, supply.app_id, PoolOptIn(!supply.listed)) } }
                        }) { Text(lcText(if (supply.listed) "Pause recruitment" else "Resume recruitment", if (supply.listed) "暂停招募" else "恢复招募")) }
                    }
                }
            }
        }
    }
}
