package com.launchcircle.testers.feature.launch

import android.content.Intent
import android.net.Uri
import android.util.Patterns
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Groups
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.core.model.TesterGroupAccess

@Composable
internal fun TesterGroupAccessCard(
    access: TesterGroupAccess?,
    accountEmail: String,
    loading: Boolean,
    onUpdate: (String, String) -> Unit,
    onRetry: () -> Unit,
) {
    val context = LocalContext.current
    var email by rememberSaveable(accountEmail, access?.play_email) { mutableStateOf(access?.play_email ?: accountEmail) }
    var isMember by rememberSaveable(accountEmail, access?.status, access?.play_email) { mutableStateOf(false) }
    var expanded by rememberSaveable(accountEmail, access?.status) { mutableStateOf(false) }
    var openFailed by remember { mutableStateOf(false) }
    val ready = access?.ready == true
    val pending = access?.status == "PENDING"
    val validEmail = Patterns.EMAIL_ADDRESS.matcher(email.trim()).matches()
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = if (ready) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.primaryContainer),
    ) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Surface(shape = RoundedCornerShape(14.dp), color = MaterialTheme.colorScheme.surface.copy(alpha = 0.7f)) {
                    Icon(Icons.Rounded.Groups, null, Modifier.padding(12.dp).size(26.dp), tint = MaterialTheme.colorScheme.primary)
                }
                Column(Modifier.weight(1f)) {
                    Text(lcText("BEFORE YOUR FIRST TEST", "开始测试前"), style = MaterialTheme.typography.labelSmall)
                    Text(lcText(if (ready) "Group step confirmed" else if (pending) "Waiting for group approval" else "Join the tester Google Group", if (ready) "已确认群组步骤" else if (pending) "等待群组批准" else "加入测试者 Google 群组"), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                }
            }
            Text(access?.group_email ?: "launch-circle-12-testers@googlegroups.com", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
            Text(lcText("Join this shared group once. Each app still has its own Play test link.", "只需加入这个共用群组一次；每个 App 仍有各自的 Play 测试链接。"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (com.launchcircle.testers.BuildConfig.USE_DEMO_REPOSITORY) {
                Text(
                    lcText("Demo mode: confirmations are saved locally for preview and are not sent to the live service or verified by Google.", "演示模式：确认仅保存在本机供预览，不会发送到线上服务，也不会由 Google 验证。"),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.tertiary,
                )
            }
            if (access == null) {
                Text(lcText("We couldn’t load your saved access. Retry before starting a test.", "暂时无法读取已保存的访问状态。开始测试前请重试。"))
                OutlinedButton(onClick = onRetry, enabled = !loading) { Text(lcText("Retry access check", "重新读取访问状态")) }
            } else {
                if (ready && !expanded) {
                    Text(lcText("Play account: ", "Play 账号：") + access.play_email)
                    Text(lcText("Saved from your confirmation. Join each app’s Play test separately.", "已保存你的确认。每个 App 仍需单独加入 Play 闭测。"), style = MaterialTheme.typography.bodySmall)
                    TextButton(onClick = { expanded = true }) { Text(lcText("Changed account or left the group?", "更换了账号或已退出群组？")) }
                } else {
                    Text(lcText("Use the same Google account for the group, Play test link and Play Store.", "群组、Play 测试链接和 Play 商店必须使用同一个 Google 账号。"))
                    OutlinedTextField(value = email, onValueChange = { email = it; isMember = false }, label = { Text(lcText("Your Google Play email", "你的 Google Play 邮箱")) }, singleLine = true, enabled = !loading, modifier = Modifier.fillMaxWidth())
                    Button(onClick = {
                        openFailed = runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(access.group_url))) }.isFailure
                    }, enabled = !loading, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(lcText("1 · Open group invite link", "1 · 打开群组邀请链接")) }
                    if (openFailed) Text(lcText("Open this link in your browser: ", "请在浏览器打开：") + access.group_url, color = MaterialTheme.colorScheme.error)
                    Text(lcText("Choose Join group. A pending request is not membership—wait for approval.", "在网页选择加入群组。申请待批准不代表已加入，请等待批准。"), style = MaterialTheme.typography.bodySmall)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = isMember, onCheckedChange = { isMember = it }, enabled = !loading)
                        Text(lcText("I am a member with the email above", "我已用上述邮箱成为正式成员"), modifier = Modifier.weight(1f))
                    }
                    Button(onClick = { onUpdate(email.trim(), "SELF_CONFIRMED") }, enabled = !loading && validEmail && isMember, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                        Text(lcText("2 · Save my confirmation", "2 · 保存我的确认"))
                    }
                    TextButton(onClick = { onUpdate(email.trim(), "PENDING") }, enabled = !loading && validEmail) { Text(lcText("My request is awaiting approval", "我的申请正在等待批准")) }
                    if (ready || pending) TextButton(onClick = { onUpdate(email.trim(), "NOT_JOINED") }, enabled = !loading && validEmail) { Text(lcText("Reset access / use another account", "重置访问状态／使用其他账号")) }
                    Text(lcText("This is your report, not automatic Google verification. You can browse apps while access is pending.", "这是你的操作确认，系统不会自动验证 Google 成员身份。等待期间仍可浏览应用。"), style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

@Composable
internal fun TestFlowStep(number: Int, title: String, detail: String, complete: Boolean = false, current: Boolean = false) {
    Row(Modifier.fillMaxWidth().padding(vertical = 5.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        Surface(shape = RoundedCornerShape(12.dp), color = if (complete || current) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceContainerHighest) {
            Text(if (complete) "✓" else number.toString(), Modifier.padding(horizontal = 13.dp, vertical = 9.dp), color = if (complete || current) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant, fontWeight = FontWeight.Bold)
        }
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
