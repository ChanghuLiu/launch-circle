package com.launchcircle.testers.feature.launch

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.BuildConfig

// versionCode, never the display name, determines whether an update is required.
@androidx.annotation.Keep
data class AndroidVersionPolicy(
    val latest_version_code: Int,
    val latest_version_name: String,
    val play_url: String,
    val apk_url: String?,
) {
    fun requiresUpdate(installedCode: Int) = latest_version_code > installedCode
}

@Composable
fun RequireCurrentVersion(policy: AndroidVersionPolicy?, checking: Boolean, failed: Boolean, onRetry: () -> Unit, content: @Composable () -> Unit) {
    val context = LocalContext.current
    var openFailed by remember { mutableStateOf(false) }
    val required = policy?.requiresUpdate(BuildConfig.VERSION_CODE) == true
    // Keep form state mounted during foreground checks; the surface below blocks input.
    val canShowContent = !failed && !required && policy != null
    if (canShowContent) content()
    if (!checking && canShowContent) return
    val directInstall = BuildConfig.DEBUG
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
                    Text(lcText("Installed: ", "当前版本：") + BuildConfig.VERSION_NAME + " · " + BuildConfig.VERSION_CODE)
                    Text(lcText("Latest: ", "最新版本：") + policy!!.latest_version_name + " · " + policy!!.latest_version_code)
                    if (directInstall) Text(lcText("Test APK: download, open the file and allow the Android update. Keep the existing app installed to preserve your data.", "独立测试版：下载后打开 APK，按 Android 提示更新。保留现有 App，直接覆盖安装即可保留数据。"))
                    Button(onClick = {
                        val url = if (directInstall) {
                            policy?.apk_url?.takeIf { it == "/android-update.apk" }?.let { BuildConfig.API_BASE_URL.trimEnd('/') + it }
                        } else policy?.play_url?.takeIf { it == "https://play.google.com/store/apps/details?id=com.launchcircle.testers" }
                        openFailed = url == null || runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }.isFailure
                    }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(lcText(if (directInstall) "Download update APK" else "Update on Google Play", if (directInstall) "下载更新 APK" else "前往 Google Play 更新")) }
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
