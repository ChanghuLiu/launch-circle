package com.launchcircle.testers.feature.launch

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.R
import com.launchcircle.testers.core.model.MissionEvidenceContext
import com.launchcircle.testers.core.model.MissionRunRequest
import com.launchcircle.testers.core.model.MissionStepEvidence
import com.launchcircle.testers.core.model.TestAssignment
import com.launchcircle.testers.core.model.TestMission
import com.launchcircle.testers.core.model.missionEvidenceOutcome
import java.util.UUID

@Composable
fun EvidenceAssignmentScreen(
    assignment: TestAssignment,
    missions: List<TestMission>,
    loading: Boolean,
    onOptIn: () -> Unit,
    onInstalled: () -> Unit,
    onMission: (TestMission) -> Unit,
) {
    val uri = LocalUriHandler.current
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(assignment.app_name, style = MaterialTheme.typography.headlineMedium)
        Text(stringResource(R.string.evidence_guided_test))
        OutlinedButton(
            onClick = { uri.openUri(assignment.opt_in_url) },
            enabled = !loading, modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.open_play_testing_link)) }
        if (assignment.status == "ASSIGNED") {
            Button(onClick = onOptIn, enabled = !loading, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.confirm_opt_in))
            }
        } else if (assignment.status == "OPTED_IN") {
            Button(onClick = onInstalled, enabled = !loading, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.confirm_installed))
            }
        }
        missions.forEach { mission ->
            OutlinedButton(
                onClick = { onMission(mission) },
                enabled = !loading && mission.status in setOf("AVAILABLE", "COMPLETED"),
                modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.evidence_mission_day, mission.scheduled_day)) }
        }
        if (missions.isEmpty() && assignment.status !in setOf("ASSIGNED", "OPTED_IN")) {
            Text(stringResource(R.string.evidence_no_missions))
        }
    }
}

@Composable
fun MissionEvidenceScreen(
    context: MissionEvidenceContext?,
    loading: Boolean,
    savedId: String?,
    onSubmit: (MissionRunRequest) -> Unit,
    executionSource: String? = "HUMAN_MANUAL",
    retestOfId: String? = null,
    onHistory: (() -> Unit)? = null,
) {
    if (context == null) {
        Text(stringResource(R.string.evidence_loading), modifier = Modifier.padding(20.dp))
        return
    }
    var version by rememberSaveable(context.mission_id) { mutableStateOf("") }
    var observations by rememberSaveable(context.mission_id) {
        mutableStateOf(List(context.steps.size) { "" })
    }
    var outcomes by rememberSaveable(context.mission_id) {
        mutableStateOf(List(context.steps.size) { "NOT_RUN" })
    }
    var note by rememberSaveable(context.mission_id) { mutableStateOf("") }
    var requestKey by rememberSaveable(context.mission_id, executionSource, retestOfId) {
        mutableStateOf(UUID.randomUUID().toString())
    }
    val uri = LocalUriHandler.current
    val result = missionEvidenceOutcome(outcomes)
    val observedBuild = version.toIntOrNull()
    val expectedBuild = context.expected_version_code
    val readOnly = loading || savedId != null
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(stringResource(R.string.evidence_record_result), style = MaterialTheme.typography.headlineSmall)
        Text(context.goal)
        if (onHistory != null) OutlinedButton(onClick = onHistory, enabled = !loading) {
            Text(stringResource(R.string.evidence_history))
        }
        OutlinedButton(onClick = {
            uri.openUri("https://play.google.com/store/apps/details?id=${context.package_name}")
        }) { Text(stringResource(R.string.evidence_open_app_listing)) }
        if (expectedBuild == null) Text(stringResource(R.string.evidence_candidate_missing))
        else Text(stringResource(R.string.evidence_candidate_build, expectedBuild))
        OutlinedTextField(
            value = version,
            onValueChange = { version = it.filter(Char::isDigit).take(9); requestKey = UUID.randomUUID().toString() },
            label = { Text(stringResource(R.string.evidence_observed_build)) },
            enabled = !readOnly, modifier = Modifier.fillMaxWidth(),
        )
        context.steps.forEachIndexed { index, instruction ->
            Text("${index + 1}. $instruction", style = MaterialTheme.typography.titleSmall)
            OutlinedTextField(
                value = observations[index],
                onValueChange = { value ->
                    observations = observations.mapIndexed { i, old -> if (i == index) value.take(2000) else old }
                    requestKey = UUID.randomUUID().toString()
                },
                label = { Text(stringResource(R.string.evidence_actual_observation)) },
                enabled = !readOnly, modifier = Modifier.fillMaxWidth(),
            )
            OutlinedButton(
                enabled = !readOnly,
                onClick = {
                    val choices = listOf("NOT_RUN", "PASS", "FAIL", "BLOCKED")
                    outcomes = outcomes.mapIndexed { i, old ->
                        if (i == index) choices[(choices.indexOf(old) + 1) % choices.size] else old
                    }
                    requestKey = UUID.randomUUID().toString()
                }, modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.evidence_step_result, outcomes[index])) }
        }
        OutlinedTextField(
            value = note,
            onValueChange = { note = it.take(2000); requestKey = UUID.randomUUID().toString() },
            label = { Text(stringResource(R.string.evidence_note)) },
            enabled = !readOnly, modifier = Modifier.fillMaxWidth(),
        )
        Text(stringResource(R.string.evidence_observation_help))
        if (savedId != null) Text(stringResource(R.string.evidence_saved))
        Button(
            enabled = !readOnly && executionSource != null && expectedBuild != null && observedBuild != null && observedBuild > 0 &&
                result != null && observations.all { it.isNotBlank() } &&
                (expectedBuild == observedBuild || result == "BLOCKED") &&
                (retestOfId == null || expectedBuild == observedBuild),
            onClick = {
                onSubmit(MissionRunRequest(
                    idempotency_key = requestKey, result = checkNotNull(result),
                    execution_source = checkNotNull(executionSource), retest_of_id = retestOfId,
                    package_name = context.package_name, version_code = checkNotNull(observedBuild),
                    expected_version_code = checkNotNull(expectedBuild),
                    steps = context.steps.mapIndexed { index, instruction ->
                        MissionStepEvidence(instruction, instruction, observations[index], outcomes[index])
                    }, note = note,
                ))
            }, modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.evidence_save)) }
    }
}
