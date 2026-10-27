package com.launchcircle.testers.feature.launch

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.R

@Composable
internal fun lcText(en: String, zh: String): String = if (LocalConfiguration.current.locales[0].language == "zh") zh else en

@Composable
fun LaunchAppHeader(onBack: (() -> Unit)? = null) {
    var guide by rememberSaveable { mutableStateOf(false) }
    Surface(tonalElevation = 2.dp) {
        Row(Modifier.fillMaxWidth().statusBarsPadding().heightIn(min = 56.dp).padding(horizontal = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            if (onBack != null) IconButton(onClick = onBack, modifier = Modifier.size(48.dp)) {
                Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = lcText("Back", "返回"))
            }
            Image(painterResource(R.drawable.launch_circle_logo), contentDescription = null, modifier = Modifier.size(36.dp).clip(RoundedCornerShape(8.dp)))
            Spacer(Modifier.width(8.dp))
            Text("Launch Circle", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f), maxLines = 1)
            TextButton(onClick = { guide = true }, modifier = Modifier.heightIn(min = 48.dp)) { Text(lcText("Help", "帮助")) }
        }
    }
    if (guide) AlertDialog(onDismissRequest = { guide = false }, title = { Text(lcText("Getting started", "新手使用指南")) },
        text = {
            Column(Modifier.heightIn(max = 440.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Text(lcText("1 · Add your app\nPaste its Google Play store/test link, enter a name and 2–4 test steps. Package and test link are detected; no developer account number is required.", "1 · 添加自己的 App\n粘贴 Google Play 商店链接或闭测链接，填写应用名称和 2–4 条测试步骤。包名和测试链接自动识别，不用填写开发者账号 ID。"))
                Text(lcText("2 · Set up Play access\nIn Play Console, add the displayed Google Group to Closed testing → Testers. Save, then confirm in Launch Circle only after completing it.", "2 · 配置测试访问\n在 Play Console 的封闭测试 → 测试者，添加页面显示的 Google 群组并保存。完成后返回确认，不要提前勾选。"))
                Text(lcText("3 · Join your App Group\nYour configured app is matched automatically. Open your group and join. One app per ordinary account; 15 developer slots per group.", "3 · 加入互测小组\n完成配置后自动匹配小组。在首页打开自己的小组并确认加入。普通账号只能添加一个 App，每组最多 15 个开发者席位。"))
                Text(lcText("4 · Test other apps\nOpen Tests. Join each app's Google Group if needed, opt in on Google Play and install using the same Google account. Confirm only the steps you completed.", "4 · 测试其他成员的 App\n打开“我的测试”。首次参加时加入该 App 的 Google 群组，再用同一个 Google 账号在 Play 加入测试并安装。只确认真正完成的步骤。"))
                Text(lcText("5 · Send feedback\nRun the displayed task and submit real results. Submitted tasks are locked until a new task becomes due. Check feedback for your own app in My Launch.", "5 · 提交反馈\n按任务步骤实际操作，再提交结果和问题。已提交的任务不可重复操作；新任务到期后才重新开放。在“我的发布”查看自己 App 的反馈。"))
                Text(lcText("Pause vs leave\nPausing keeps your slot and tasks. Leaving stops mutual tasks, releases your slot and pauses your app; history stays. Resume from My Launch. Group occupancy does not prove Google Play eligibility.", "暂停与退出\n暂停招募会保留席位和任务。退出会停止互测、释放席位并暂停自己的 App，历史反馈保留；可从“我的发布”恢复。组内席位数不代表 Google Play 合格测试人数。"))
                Text(lcText("If verification is unavailable, give support the Play link for ownership review. Never share passwords or keys. External publishers may need review before they can publish.", "若提示需要所有权审核，把 Play 链接交给管理员，不要提供密码或密钥。外部开发者可能需要审核后才能发布。"))
            }
        }, confirmButton = { TextButton(onClick = { guide = false }) { Text(lcText("Got it", "知道了")) } })
}
