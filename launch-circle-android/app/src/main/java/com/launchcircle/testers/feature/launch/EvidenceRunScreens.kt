package com.launchcircle.testers.feature.launch

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.R
import com.launchcircle.testers.core.model.EvidenceRunDetail
import com.launchcircle.testers.core.model.MissionRunRequest

@Composable
fun EvidenceRunDetailScreen(detail: EvidenceRunDetail?, loading: Boolean, onRetest: () -> Unit) {
    if (detail == null) {
        Text(stringResource(if (loading) R.string.evidence_loading else R.string.publisher_evidence_load_failed),
            modifier = Modifier.padding(20.dp))
        return
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(stringResource(R.string.evidence_view_details), style = MaterialTheme.typography.headlineMedium)
        Text(detail.app_name)
        Text(stringResource(R.string.evidence_run_metadata, detail.run.result,
            detail.run.execution_source, detail.run.version_code, detail.run.device_model, detail.run.android_api))
        Text(detail.run.recorded_at)
        detail.run.retest_of_id?.let { Text(stringResource(R.string.evidence_retest_of, it)) }
        detail.run.details.steps.forEachIndexed { i, step ->
            Text("${i + 1}. ${step.instruction}", style = MaterialTheme.typography.titleMedium)
            Text(stringResource(R.string.evidence_detail_expected, step.expected))
            Text(stringResource(R.string.evidence_detail_actual, step.actual))
            Text(stringResource(R.string.evidence_detail_result, step.result))
        }
        if (detail.run.details.note.isNotBlank()) Text(detail.run.details.note)
        detail.fix?.let {
            Text(stringResource(R.string.publisher_evidence_fix_build, it.target_version_code))
            Text(it.description)
        }
        Text(stringResource(R.string.evidence_retest_scope))
        if (detail.run.result == "FAIL") {
            if (detail.retest_context == null) Text(stringResource(R.string.evidence_retest_unavailable))
            OutlinedButton(onClick = onRetest, enabled = !loading && detail.retest_context != null,
                modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.evidence_begin_retest)) }
        }
    }
}

@Composable
fun EvidenceRetestScreen(
    detail: EvidenceRunDetail?, loading: Boolean, savedId: String?,
    onSubmit: (MissionRunRequest) -> Unit,
) {
    if (detail?.retest_context == null) {
        Text(stringResource(R.string.evidence_retest_unavailable), modifier = Modifier.padding(20.dp))
        return
    }
    var source by rememberSaveable(detail.run.id) { mutableStateOf<String?>(null) }
    Column(Modifier.fillMaxSize()) {
        Column(Modifier.padding(horizontal = 20.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(stringResource(R.string.evidence_retest_scope))
            if (savedId == null) {
                val sources = if (detail.can_submit_manual) listOf("HUMAN_MANUAL", "CODEX_ASSISTED")
                    else listOf("CODEX_ASSISTED")
                sources.forEach { choice ->
                    OutlinedButton(onClick = { source = choice }, enabled = !loading) {
                        Text(stringResource(if (choice == "HUMAN_MANUAL") R.string.evidence_source_manual
                            else R.string.evidence_source_assisted) + if (source == choice) " ✓" else "")
                    }
                }
            }
        }
        Box(Modifier.weight(1f)) {
            MissionEvidenceScreen(detail.retest_context, loading, savedId, onSubmit,
                executionSource = source, retestOfId = detail.run.id)
        }
    }
}


@Composable
fun EvidenceHistoryScreen(runs: List<com.launchcircle.testers.core.model.EvidenceRunFull>, onDetail: (String) -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(stringResource(R.string.evidence_history), style = MaterialTheme.typography.headlineMedium)
        if (runs.isEmpty()) Text(stringResource(R.string.evidence_history_empty))
        runs.forEach { run ->
            OutlinedButton(onClick = { onDetail(run.id) }, modifier = Modifier.fillMaxWidth()) {
                Text("${run.result} · ${run.execution_source} · v${run.version_code}\n${run.recorded_at}")
            }
        }
    }
}
