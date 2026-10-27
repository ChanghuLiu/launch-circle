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
) {
    val api = remember(baseUrl) { ApiFactory.create(baseUrl) }
    val client = remember(tokens) { PoolClient(tokens, refresh) }
    val scope = rememberCoroutineScope()
    var groups by remember { mutableStateOf(emptyList<AppTestGroup>()) }
    var selectedGroupId by rememberSaveable { mutableStateOf<String?>(null) }
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
    LaunchedEffect(Unit) { action {} }
    leaveTarget?.let { groupId ->
        AlertDialog(onDismissRequest = { if (!busy) leaveTarget = null },
            title = { Text("Leave App Group?") },
            text = { Text("Your app's recruitment will pause and reciprocal tasks in this group will stop. Feedback and history are kept. The group reopens the slot for another developer. Google Play opt-in is managed separately.") },
            confirmButton = { TextButton(enabled = !busy, onClick = {
                leaveTarget = null
                action { client.call { api.leaveAppGroup(it, groupId) }; selectedGroupId = null; notice = "You left the group. Resume recruitment in My Launch when ready." }
            }) { Text("Leave group") } },
            dismissButton = { TextButton(enabled = !busy, onClick = { leaveTarget = null }) { Text("Stay in group") } })
    }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item {
            Text(if (home) "App Groups" else "My launch", style = MaterialTheme.typography.headlineLarge)
            Text(if (home) "Add your app, get matched to an App Group, then test the other members’ apps." else "Pause or resume recruitment here. Pausing keeps your group slot and existing tasks; use Leave group to stop mutual testing and release the slot.")
            if (home) {
                TextButton(onClick = { rulesExpanded = !rulesExpanded }) { Text(if (rulesExpanded) "Hide group rules" else "How groups work") }
                if (rulesExpanded) Text("15 developers maximum · 1 app per developer · test up to 14 other apps. Full groups stop receiving new apps. Leaving releases your slot and pauses your app; history stays. Pausing recruitment keeps your slot; leaving releases it. New developers are matched into open slots. App Groups organize mutual testing; Google Groups provide Play test access. App slots do not prove active testers or Google eligibility.")
            }
            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            notice?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
            OutlinedButton(onClick = { action {} }, enabled = !busy) { Text("Refresh") }
            if (home && selectedGroupId == null && loaded && (admin || ownedCount == 0)) Button(onClick = onAdd, enabled = !busy) { Text("Add my app") }
            if (home && loaded && ownedCount > 0 && groups.none { it.my_group }) {
                Text("Your app is not recruiting in a group. Finish setup or resume recruitment in My Launch.")
                OutlinedButton(onClick = onLaunch, enabled = !busy) { Text("Open My Launch") }
            }
        }
        if (home) {
            val selected = groups.firstOrNull { it.id == selectedGroupId }
            if (selected == null) {
                if (loaded && groups.isEmpty()) item { Text("No groups yet. Add your app and finish test access setup; matching is automatic.") }
                items(groups, key = { it.id }) { group ->
                    OutlinedCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(group.name, style = MaterialTheme.typography.titleLarge)
                            Text(if (group.my_group) "Your app is matched to this group" else "Community testing group")
                            Text("${group.occupied_slots} / ${group.capacity} app slots · " + if (group.status == "FORMING") "Open for matching" else "Full · new apps closed")
                            Button(enabled = !busy, onClick = { selectedGroupId = group.id }) { Text(if (group.joined) "Open my group" else "View group") }
                            group.apps.take(4).forEach { app ->
                                androidx.compose.foundation.layout.Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                    AppIcon(app.name, app.icon_url)
                                    Text(app.name, modifier = Modifier.weight(1f))
                                }
                            }
                            if (group.apps.size > 4) Text("+ ${group.apps.size - 4} more apps")
                        }
                    }
                }
            } else {
                item {
                    OutlinedButton(onClick = { selectedGroupId = null }) { Text("Back to groups") }
                    Text(selected.name, style = MaterialTheme.typography.headlineMedium)
                    Text("Joining agrees to test this group’s current and future apps, up to 14 other developers, and send real feedback. Play enrollment and installation are separate actions. A forming group does not yet provide 12 testers.")
                    when {
                        selected.joined -> {
                            Button(onClick = {}, enabled = false) { Text("Group joined") }
                            OutlinedButton(enabled = !busy, onClick = onTests) { Text("Open my group tests") }
                        }
                        selected.my_group && !selected.ready_to_join -> OutlinedButton(onClick = onLaunch, enabled = !busy) { Text("Resume recruitment in My Launch") }
                        selected.my_group -> Button(enabled = !busy, onClick = {
                            action {
                                client.call { api.joinAppGroup(it, selected.id) }
                                notice = "Group joined. Open Tests to complete each app's Play opt-in and installation."
                                onTests()
                            }
                        }) { Text("Join group and test its apps") }
                        ownedCount == 0 -> Button(enabled = !busy && loaded, onClick = onAdd) { Text("Add my app to get matched") }
                        else -> Text("Your app belongs to its automatically matched group. Open that group to join.")
                    }
                }
                item {
                    if (selected.my_group || selected.joined) OutlinedButton(enabled = !busy, onClick = { leaveTarget = selected.id }) { Text("Leave this group") }
                }
                items(selected.apps, key = { it.app_id }) { app ->
                    OutlinedCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            AppIcon(app.name, app.icon_url)
                            Text(app.name, style = MaterialTheme.typography.titleLarge)
                            if (app.owned) Text("Your app")
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
                        }) { Text(if (supply.listed) "Pause recruitment" else "Resume recruitment") }
                    }
                }
            }
        }
    }
}
