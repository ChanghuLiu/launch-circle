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
    groupReady: Boolean,
    sharedGroupUrl: String,
    accessCard: @Composable () -> Unit,
    onOptIn: () -> Unit,
    onInstalled: () -> Unit,
    onMission: (TestMission) -> Unit,
) {
    val uri = LocalUriHandler.current
    val needsGroupMembership = assignment.status == "ASSIGNED" && !assignment.google_group_url.isNullOrBlank() && assignment.google_group_url != sharedGroupUrl
    var groupMembershipConfirmed by rememberSaveable(assignment.id) { mutableStateOf(!needsGroupMembership) }
    var playLinkOpened by rememberSaveable(assignment.id) { mutableStateOf(false) }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(assignment.app_name, style = MaterialTheme.typography.headlineMedium)
        Text(lcText("Follow these steps in order. Your progress is saved to your account.", "按顺序完成以下步骤，进度会保存到你的账号。"), color = MaterialTheme.colorScheme.onSurfaceVariant)
        TestFlowStep(1, lcText("Google Group", "Google 群组"), lcText("Join once with your Play account", "使用 Play 账号加入一次"), complete = groupReady, current = !groupReady)
        accessCard()
        if (!groupReady) {
            Text(lcText("Complete the group step above to unlock this app’s Play test link.", "完成上方群组步骤后，即可打开这个 App 的 Play 测试链接。"))
            return@Column
        }
        if (needsGroupMembership) {
            Text(
                lcText("This app also needs its own Google Group", "这个 App 还要求加入它自己的 Google 群组"),
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                lcText(
                    "Use the same Google account as Play Store. If you have already joined, skip to the confirmation below. Wait for approval if Google Groups shows a pending request.",
                    "请使用与 Play 商店相同的 Google 账号。如果你已加入，可直接在下方确认；如果 Google 群组显示申请待批准，请先等待批准。",
                ),
            )
            OutlinedButton(
                onClick = { uri.openUri(checkNotNull(assignment.google_group_url)) },
                enabled = !loading,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(lcText("Open group join link", "打开群组加入链接")) }
            Text(
                lcText(
                    "Launch Circle cannot verify group membership automatically.",
                    "Launch Circle 无法自动核实群组成员身份。",
                ),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Button(
                onClick = { groupMembershipConfirmed = true },
                enabled = !loading,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(lcText("I have joined this group", "我已加入此群组")) }
        }

        TestFlowStep(2, lcText("Join this app’s Play test", "加入此 App 的 Play 闭测"), lcText("Choose Become a tester on Google Play", "在 Google Play 页面选择成为测试者"), complete = assignment.status != "ASSIGNED", current = assignment.status == "ASSIGNED")
        Text(lcText("Joining the Google Group does not enroll you in this app. Use the same Play account.", "加入 Google 群组不会自动加入这个 App，请继续使用同一个 Play 账号。"), style = MaterialTheme.typography.bodySmall)
        OutlinedButton(
            onClick = { uri.openUri(assignment.opt_in_url); playLinkOpened = true },
            enabled = !loading && groupReady && groupMembershipConfirmed,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.open_play_testing_link)) }
        if (assignment.status == "ASSIGNED") {
            Button(
                onClick = onOptIn,
                enabled = !loading && groupReady && groupMembershipConfirmed && playLinkOpened,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.confirm_opt_in)) }
        }
        TestFlowStep(3, lcText("Install from Google Play", "从 Google Play 安装"), lcText("Install and open the app, then return here", "安装并打开应用，然后返回这里"), complete = assignment.status in setOf("INSTALLED", "ACTIVE", "COMPLETED"), current = assignment.status == "OPTED_IN")
        if (assignment.status == "OPTED_IN") {
            Button(onClick = onInstalled, enabled = !loading, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.confirm_installed))
            }
        }
        TestFlowStep(4, lcText("Test and send feedback", "完成测试并提交反馈"), lcText("Follow the mission and record what happened", "按任务要求操作，并记录实际结果"), current = assignment.status in setOf("INSTALLED", "ACTIVE"))
        missions.forEach { mission ->
            OutlinedButton(
                onClick = { onMission(mission) },
                enabled = !loading && assignment.status in setOf("INSTALLED", "ACTIVE", "COMPLETED") && !mission.feedback_submitted && mission.status in setOf("AVAILABLE", "COMPLETED"),
                modifier = Modifier.fillMaxWidth(),
            ) { Text(if (mission.feedback_submitted) "Day ${mission.scheduled_day} · Feedback submitted" else stringResource(R.string.evidence_mission_day, mission.scheduled_day)) }
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
