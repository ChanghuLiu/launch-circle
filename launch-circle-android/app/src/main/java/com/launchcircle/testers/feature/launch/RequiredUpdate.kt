package com.launchcircle.testers.feature.launch

import android.app.Activity
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.google.android.play.core.appupdate.AppUpdateManagerFactory
import com.google.android.play.core.appupdate.AppUpdateOptions
import com.google.android.play.core.install.model.AppUpdateType
import com.google.android.play.core.install.model.UpdateAvailability

// versionCode, never the display name, determines whether an update is required.
@androidx.annotation.Keep
data class AndroidVersionPolicy(
    val latest_version_code: Int,
    val latest_version_name: String,
    val play_url: String,
) {
    fun requiresUpdate(installedCode: Int) = latest_version_code > installedCode
}

@Composable
fun RequireCurrentVersion(policy: AndroidVersionPolicy?, checking: Boolean, failed: Boolean, onRetry: () -> Unit, content: @Composable () -> Unit) {
    val context = LocalContext.current
    var openFailed by remember { mutableStateOf(false) }
    var updateCheckFailed by remember { mutableStateOf(false) }
    val appUpdateManager = remember(context) { AppUpdateManagerFactory.create(context) }
    val updateLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartIntentSenderForResult(),
    ) { result ->
        if (result.resultCode != Activity.RESULT_OK) updateCheckFailed = true
    }
    val required = policy?.requiresUpdate(com.launchcircle.testers.BuildConfig.VERSION_CODE) == true
    // Play requires an interrupted immediate update to resume on foreground entry.
    androidx.lifecycle.compose.LifecycleEventEffect(androidx.lifecycle.Lifecycle.Event.ON_RESUME) {
        appUpdateManager.appUpdateInfo.addOnSuccessListener { info ->
            if (info.updateAvailability() == UpdateAvailability.DEVELOPER_TRIGGERED_UPDATE_IN_PROGRESS) {
                runCatching {
                    appUpdateManager.startUpdateFlowForResult(
                        info,
                        updateLauncher,
                        AppUpdateOptions.newBuilder(AppUpdateType.IMMEDIATE).build(),
                    )
                }.onSuccess { started -> updateCheckFailed = !started }
                    .onFailure { updateCheckFailed = true }
            }
        }
    }
    // Keep form state mounted during foreground checks; the surface below blocks input.
    val canShowContent = !failed && !required && policy != null
    if (canShowContent) content()
    if (!checking && canShowContent) return
    Surface(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(24.dp), verticalArrangement = Arrangement.spacedBy(20.dp, Alignment.CenterVertically)) {
            Text("Launch Circle", style = MaterialTheme.typography.titleLarge)
            when {
                checking -> {
                    CircularProgressIndicator()
                    Text(lcText("Checking for updates…", "正在检查新版本…"))
                }
                required -> {
                    Text(lcText("Update required", "请更新后继续"), style = MaterialTheme.typography.headlineMedium)
                    Text(lcText("A newer version is available. Update to continue using Launch Circle.", "已有新版本，请更新后继续使用 Launch Circle。"))
                    Text(lcText("Installed: ", "当前版本：") + com.launchcircle.testers.BuildConfig.VERSION_NAME + " · " + com.launchcircle.testers.BuildConfig.VERSION_CODE)
                    Text(lcText("Latest: ", "最新版本：") + policy.latest_version_name + " · " + policy.latest_version_code)
                    Button(onClick = {
                        updateCheckFailed = false
                        appUpdateManager.appUpdateInfo
                            .addOnSuccessListener { info ->
                                val canStart = info.updateAvailability() == UpdateAvailability.UPDATE_AVAILABLE &&
                                    info.isUpdateTypeAllowed(AppUpdateType.IMMEDIATE)
                                val inProgress = info.updateAvailability() == UpdateAvailability.DEVELOPER_TRIGGERED_UPDATE_IN_PROGRESS
                                if (canStart || inProgress) {
                                    runCatching {
                                        appUpdateManager.startUpdateFlowForResult(
                                            info,
                                            updateLauncher,
                                            AppUpdateOptions.newBuilder(AppUpdateType.IMMEDIATE).build(),
                                        )
                                    }.onSuccess { started -> updateCheckFailed = !started }
                                        .onFailure { updateCheckFailed = true }
                                } else {
                                    updateCheckFailed = true
                                }
                            }
                            .addOnFailureListener { updateCheckFailed = true }
                    }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(lcText("Update now in Google Play", "立即通过 Google Play 更新")) }
                    OutlinedButton(onClick = {
                        val url = policy.play_url.takeIf { it == "https://play.google.com/store/apps/details?id=com.launchcircle.testers" }
                        openFailed = url == null || runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }.isFailure
                    }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(lcText("Open Google Play", "打开 Google Play")) }
                    if (updateCheckFailed) Text(lcText("Google Play can't start an in-app update for this installation. Open Google Play to install or update the Play version.", "Google Play 无法为此安装启动应用内更新。请打开 Google Play 安装或更新 Play 版本。"), color = MaterialTheme.colorScheme.error)
                    if (openFailed) Text(lcText("Could not open the update. Check your connection and retry, or contact the administrator.", "无法打开更新，请检查网络后重试，或联系管理员。"), color = MaterialTheme.colorScheme.error)
                    OutlinedButton(onClick = { onRetry() }, modifier = Modifier.fillMaxWidth()) { Text(lcText("I've updated / Check again", "已更新／重新检查")) }
                }
                else -> {
                    Text(lcText("Couldn't check for updates", "暂时无法检查新版本"), style = MaterialTheme.typography.headlineMedium)
                    Text(lcText("Connect to the internet and retry to continue.", "请连接网络后重试，检查完成后即可继续。"))
                    Button(onClick = { onRetry() }, modifier = Modifier.fillMaxWidth()) { Text(lcText("Retry", "重试")) }
                }
            }
        }
    }
}
