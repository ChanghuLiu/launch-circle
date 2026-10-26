package com.launchcircle.testers.feature.launch

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
fun SharedPoolScreen(baseUrl: String, tokens: TokenStore, refresh: suspend () -> Boolean) {
    val api = remember(baseUrl) { ApiFactory.create(baseUrl) }
    val client = remember(tokens) { PoolClient(tokens, refresh) }
    val scope = rememberCoroutineScope()
    var preference by remember { mutableStateOf<PoolPreference?>(null) }
    var opportunities by remember { mutableStateOf(emptyList<PoolOpportunity>()) }
    var supplies by remember { mutableStateOf(emptyList<PoolSupply>()) }
    var intakes by remember { mutableStateOf(emptyList<AppIntakeStatus>()) }
    var intakeOpen by rememberSaveable { mutableStateOf(false) }
    var appName by rememberSaveable { mutableStateOf("") }
    var packageName by rememberSaveable { mutableStateOf("") }
    var publisherId by rememberSaveable { mutableStateOf("") }
    var steps by rememberSaveable { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var notice by remember { mutableStateOf<String?>(null) }
    suspend fun load() {
        intakes = client.call { api.appIntakes(it) }
        preference = client.call { api.poolPreference(it) }
        opportunities = client.call { api.poolOpportunities(it) }
        val owned = client.call { api.apps(it) }
        supplies = owned.map { app -> client.call { api.poolSupply(it, app.id) } }
    }
    fun action(block: suspend () -> Unit) {
        if (busy) return
        busy = true
        error = null
        scope.launch {
            try { block(); load() }
            catch (failure: Exception) {
                if (failure is kotlinx.coroutines.CancellationException) throw failure
                error = when (failure) {
                    is HttpException -> when (failure.code()) {
                        401 -> "Your session expired. Sign in again."
                        404 -> "This opportunity is no longer available. Refresh to continue."
                        422 -> "Check the app name, package, numeric publisher account ID and 1–5 workflow steps."
                        409 -> "Not available yet: check group setup, workflow steps, circle capacity and the two-app limit."
                        else -> "Unable to update the pool. Please retry."
                    }
                    else -> "Unable to reach Launch Circle. Please retry."
                }
            } finally { busy = false }
        }
    }
    LaunchedEffect(Unit) { action {} }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item {
            Text("Shared tester pool", style = MaterialTheme.typography.headlineMedium)
            Text("Start with one customer. Recruit real volunteers across Launch Circles.")
            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            notice?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
            OutlinedButton(onClick = { action {} }, enabled = !busy) { Text("Refresh") }
        }
        item {
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Volunteer as a tester", style = MaterialTheme.typography.titleLarge)
                    Text("Choose each app separately. Your password is never requested. No public ratings or reviews. Accepting a task does not join Google Play automatically.")
                    preference?.let { pref ->
                        Text("Active apps: " + pref.active_apps + " / " + pref.max_concurrent_apps)
                        Button(enabled = !busy, onClick = {
                            action { client.call { api.setPoolPreference(it, PoolOptIn(!pref.enabled)) } }
                        }) { Text(if (pref.enabled) "Pause new opportunities" else "Join voluntary tester pool") }
                        if (pref.enabled) Text("You are available. Pausing stops new acceptances; existing tasks and Google Play opt-ins are unchanged.")
                    }
                }
            }
        }
        if (preference?.enabled == true) {
            item {
                Text("Choose an app", style = MaterialTheme.typography.titleLarge)
                if (opportunities.isEmpty()) Text("No available tasks right now, or your two-app limit is reached.")
            }
            items(opportunities, key = { it.app_id }) { opportunity ->
                OutlinedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(opportunity.name, style = MaterialTheme.typography.titleMedium)
                        Text(opportunity.package_name)
                        opportunity.workflow_steps.forEachIndexed { i, step -> Text("Agreed task " + (i + 1) + ": " + step) }
                        Button(enabled = !busy, onClick = {
                            action {
                                client.call { api.acceptPoolApp(it, opportunity.app_id) }
                                notice = "Task accepted. Return to Today's tests to opt in through Google Play and confirm installation separately."
                            }
                        }) { Text("Accept this app's tasks") }
                    }
                }
            }
        }
        item {
            Text("Recruit for my apps", style = MaterialTheme.typography.titleLarge)
            Text("Opening recruitment shares the app name, package and workflow steps with volunteers. Do not put private credentials in workflow steps. No participants are fabricated or guaranteed.")
            if (supplies.isEmpty()) Text("Add your first app in My Launch to recruit testers.")
        }
        item {
            OutlinedButton(enabled = !busy, onClick = { intakeOpen = !intakeOpen }) {
                Text(if (intakeOpen) "Close onboarding form" else "Request assisted app onboarding")
            }
            if (intakeOpen) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("For publishers who cannot use automatic app verification. Submit your app for private operator review. A request does not verify ownership, start testing or grant a purchase.")
                    Text("Only the publisher's first app can be provisioned through this pilot. We will ask you to demonstrate control of the package and publisher account through a secure support channel. Never submit passwords or secret keys.")
                    OutlinedTextField(value = appName, onValueChange = { appName = it }, label = { Text("App name") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = packageName, onValueChange = { packageName = it }, label = { Text("Android package name") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = publisherId, onValueChange = { publisherId = it }, label = { Text("Numeric Play developer account ID") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = steps, onValueChange = { steps = it }, label = { Text("1–5 core workflow steps, one per line") }, minLines = 3, modifier = Modifier.fillMaxWidth())
                    Button(enabled = !busy && appName.isNotBlank() && packageName.isNotBlank() && publisherId.isNotBlank() && steps.isNotBlank(), onClick = {
                        action {
                            client.call { api.submitAppIntake(it, AppIntakeRequest(appName.trim(), packageName.trim(), publisherId.trim(), steps.lines().map(String::trim).filter(String::isNotBlank))) }
                            notice = "Request submitted for private review. Testing has not started."
                            intakeOpen = false
                            appName = ""; packageName = ""; publisherId = ""; steps = ""
                        }
                    }) { Text("Submit onboarding request") }
                }
            }
        }
        items(intakes, key = { "intake-" + it.id }) { intake ->
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(intake.name, style = MaterialTheme.typography.titleMedium)
                    Text(intake.package_name)
                    Text("Onboarding: " + intake.status)
                    Text(if (intake.status == "APPROVED" && intake.app_id != null) "Your app is available in My Launch. Confirm the Google Group and test access before opening recruitment." else if (intake.status == "APPROVED") "This approved app has been removed." else "Your request is private. Support must review your package authorization before creating a campaign.")
                }
            }
        }
        items(supplies, key = { it.app_id }) { supply ->
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(supply.name, style = MaterialTheme.typography.titleMedium)
                    Text("Accepted tasks: " + supply.accepted_participants)
                    Text("Reported Play opt-in + installation: " + supply.reported_joined_and_installed)
                    Text("Missing to 12: " + supply.missing_to_minimum + ". Buffer target: 14.")
                    Text("Check continuity and eligibility in your own Play Console.")
                    if (!supply.ready_to_list) Text("Before recruiting: confirm Google Group setup and add core workflow steps with a valid Play test link.")
                    Button(enabled = !busy && (supply.listed || supply.ready_to_list), onClick = {
                        action { client.call { api.setPoolListing(it, supply.app_id, PoolOptIn(!supply.listed)) } }
                    }) { Text(if (supply.listed) "Close recruitment" else "Open recruitment") }
                }
            }
        }
    }
}
