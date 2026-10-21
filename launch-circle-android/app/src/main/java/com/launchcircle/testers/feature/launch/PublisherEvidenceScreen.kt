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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.OutlinedTextField
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
import com.launchcircle.testers.core.model.CampaignEvidenceSummary

@Composable
fun PublisherEvidenceScreen(
    summary: CampaignEvidenceSummary?,
    loading: Boolean,
    notice: String?,
    onRefresh: () -> Unit,
    onBuild: (Int, String) -> Unit,
    onFix: (String, Int, String) -> Unit,
    onDetail: (String) -> Unit,
    reportJson: String?,
    onReport: () -> Unit,
) {
    LazyColumn(
        Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Text(stringResource(R.string.publisher_evidence_title), style = MaterialTheme.typography.headlineMedium)
            Text(stringResource(R.string.publisher_evidence_limit))
            OutlinedButton(onClick = onRefresh, enabled = !loading) {
                Text(stringResource(R.string.publisher_evidence_refresh))
            }
            notice?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
            EvidenceReportActions(reportJson, loading, onReport)
        }
        if (summary != null) {
            item {
                Text(summary.package_name, style = MaterialTheme.typography.titleMedium)
                Text(stringResource(R.string.publisher_evidence_candidate,
                    summary.candidate_version_code?.toString() ?: stringResource(R.string.publisher_evidence_unset)))
            }
            item {
                OutlinedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(stringResource(R.string.publisher_evidence_people), style = MaterialTheme.typography.titleMedium)
                        Text(stringResource(R.string.publisher_evidence_assigned, summary.assigned_participants))
                        Text(stringResource(R.string.publisher_evidence_joined, summary.reported_joined_participants))
                        Text(stringResource(R.string.publisher_evidence_confirmed, summary.owner_confirmed_joined_participants))
                        Text(stringResource(R.string.publisher_evidence_continuity, summary.reported_continuous_14_days))
                        Text(stringResource(R.string.publisher_evidence_manual, summary.manual_reported_participants))
                    }
                }
            }
            item {
                OutlinedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(stringResource(R.string.publisher_evidence_devices), style = MaterialTheme.typography.titleMedium)
                        Text(stringResource(R.string.publisher_evidence_coverage, summary.current_build_device_coverage))
                        Text(stringResource(R.string.publisher_evidence_runs, summary.total_runs))
                        Text(stringResource(R.string.publisher_evidence_sources,
                            summary.execution_sources["HUMAN_MANUAL"] ?: 0,
                            summary.execution_sources["CODEX_ASSISTED"] ?: 0,
                            summary.execution_sources["AUTOMATED_RUNNER"] ?: 0))
                        Text(stringResource(R.string.publisher_evidence_results,
                            summary.current_build_results["PASS"] ?: 0, summary.current_build_results["FAIL"] ?: 0,
                            summary.current_build_results["BLOCKED"] ?: 0, summary.current_build_results["NOT_RUN"] ?: 0))
                    }
                }
            }
            item {
                EvidenceVersionForm("build-" + summary.app_id, loading,
                    stringResource(R.string.publisher_evidence_set_build), descriptionRequired = false, onSave = onBuild)
            }
            item {
                Text(stringResource(R.string.publisher_evidence_issues), style = MaterialTheme.typography.titleLarge)
                Text(stringResource(R.string.publisher_evidence_fix_help))
                if (summary.issues.isEmpty()) Text(stringResource(R.string.publisher_evidence_no_issues))
            }
            items(summary.issues, key = { it.run_id }) { issue ->
                OutlinedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(issue.state, style = MaterialTheme.typography.titleMedium)
                        Text(stringResource(R.string.publisher_evidence_failure, issue.reported_version_code))
                        Text(stringResource(R.string.publisher_evidence_run_id, issue.run_id))
                        OutlinedButton(onClick = { onDetail(issue.run_id) }, enabled = !loading) {
                            Text(stringResource(R.string.evidence_view_details))
                        }
                        if (issue.fixed_version_code != null) {
                            Text(stringResource(R.string.publisher_evidence_fix_build, issue.fixed_version_code))
                            Text(stringResource(R.string.publisher_evidence_retest,
                                issue.last_retest_result ?: stringResource(R.string.publisher_evidence_unset)))
                        } else {
                            EvidenceVersionForm(issue.run_id, loading,
                                stringResource(R.string.publisher_evidence_declare_fix)) { version, description ->
                                onFix(issue.run_id, version, description)
                            }
                        }
                    }
                }
            }
        } else if (!loading) {
            item { Text(stringResource(R.string.publisher_evidence_load_failed)) }
        }
    }
}

@Composable
private fun EvidenceVersionForm(key: String, loading: Boolean, action: String, descriptionRequired: Boolean = true, onSave: (Int, String) -> Unit) {
    var version by rememberSaveable(key) { mutableStateOf("") }
    var description by rememberSaveable(key) { mutableStateOf("") }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedTextField(version, { version = it.filter(Char::isDigit).take(9) },
            label = { Text(stringResource(R.string.publisher_evidence_version_input)) },
            enabled = !loading, modifier = Modifier.fillMaxWidth())
        if (descriptionRequired) OutlinedTextField(description, { description = it.take(2000) },
            label = { Text(stringResource(R.string.publisher_evidence_description)) },
            enabled = !loading, modifier = Modifier.fillMaxWidth())
        val parsed = version.toIntOrNull()
        Button(onClick = { onSave(checkNotNull(parsed), if (descriptionRequired) description.trim() else "Publisher confirmed candidate version") },
            enabled = !loading && parsed != null && parsed > 0 && (!descriptionRequired || description.isNotBlank()),
            modifier = Modifier.fillMaxWidth()) { Text(action) }
    }
}
