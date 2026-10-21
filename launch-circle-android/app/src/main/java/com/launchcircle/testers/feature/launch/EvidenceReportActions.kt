package com.launchcircle.testers.feature.launch

import android.content.ClipData
import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.launchcircle.testers.R
import com.launchcircle.testers.core.model.evidenceReportText
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.UUID

@Composable
fun EvidenceReportActions(reportJson: String?, loading: Boolean, onPrepare: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val savedMessage = stringResource(R.string.evidence_report_saved)
    val failedMessage = stringResource(R.string.evidence_report_failed)
    val shareLabel = stringResource(R.string.evidence_share_report)
    var status by remember { mutableStateOf<String?>(null) }
    var pendingContents by remember { mutableStateOf<String?>(null) }
    var saving by remember { mutableStateOf(false) }
    fun writeReport(uri: android.net.Uri?) {
        val contents = pendingContents
        pendingContents = null
        if (uri == null || contents == null) return
        scope.launch {
            saving = true
            status = try {
                withContext(Dispatchers.IO) {
                    checkNotNull(context.contentResolver.openOutputStream(uri)).bufferedWriter().use { it.write(contents) }
                }
                savedMessage
            } catch (_: Exception) {
                failedMessage
            }
            saving = false
        }
    }
    val jsonSave = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { writeReport(it) }
    val textSave = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/plain")) { writeReport(it) }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedButton(onClick = { status = null; onPrepare() }, enabled = !loading && !saving) {
            Text(stringResource(R.string.evidence_prepare_report))
        }
        if (reportJson != null) {
            Text(stringResource(R.string.evidence_report_snapshot))
            OutlinedButton(onClick = {
                pendingContents = reportJson
                jsonSave.launch("launch-circle-evidence.json")
            }, enabled = !loading && !saving) { Text(stringResource(R.string.evidence_save_json)) }
            OutlinedButton(onClick = {
                pendingContents = evidenceReportText(reportJson)
                textSave.launch("launch-circle-evidence.txt")
            }, enabled = !loading && !saving) { Text(stringResource(R.string.evidence_save_text)) }
            OutlinedButton(onClick = {
                scope.launch {
                    saving = true
                    try {
                        val uri = withContext(Dispatchers.IO) {
                            val directory = File(context.cacheDir, "evidence-reports").apply { mkdirs() }
                            directory.listFiles()?.filter { System.currentTimeMillis() - it.lastModified() > 86400000L }?.forEach { it.delete() }
                            val file = File(directory, "evidence-${UUID.randomUUID()}.txt")
                            file.writeText(evidenceReportText(reportJson))
                            FileProvider.getUriForFile(context, context.packageName + ".evidence.files", file)
                        }
                        val intent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_STREAM, uri)
                            clipData = ClipData.newRawUri("Testing evidence", uri)
                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                        }
                        context.startActivity(Intent.createChooser(intent, shareLabel))
                    } catch (_: Exception) {
                        status = failedMessage
                    }
                    saving = false
                }
            }, enabled = !loading && !saving) { Text(stringResource(R.string.evidence_share_report)) }
        }
        status?.let { Text(it) }
    }
}
