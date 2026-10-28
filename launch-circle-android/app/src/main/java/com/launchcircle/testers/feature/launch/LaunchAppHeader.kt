package com.launchcircle.testers.feature.launch

import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
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
fun LaunchAppHeader(onBack: (() -> Unit)? = null, guideAccountId: String? = null, onGuideAction: ((Int) -> Unit)? = null) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val prefs = remember(context) { context.getSharedPreferences("launch_circle_guide", android.content.Context.MODE_PRIVATE) }
    val key = "guide_v2_" + (guideAccountId ?: "guest")
    var guide by rememberSaveable(key) { mutableStateOf(guideAccountId != null && !prefs.getBoolean(key + "_introduced", false)) }
    var step by rememberSaveable(key) { mutableIntStateOf(prefs.getInt(key + "_step", 0).coerceIn(0, 5)) }
    var preview by remember { mutableStateOf<Int?>(null) }
    var linkFailed by remember { mutableStateOf(false) }
    fun closeGuide(completed: Boolean) {
        prefs.edit().putBoolean(key + "_introduced", true).putInt(key + "_step", if (completed) 0 else step).apply()
        guide = false
    }
    Surface(tonalElevation = 2.dp) {
        Row(Modifier.fillMaxWidth().statusBarsPadding().heightIn(min = 56.dp).padding(horizontal = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            if (onBack != null) IconButton(onClick = onBack, modifier = Modifier.size(48.dp)) {
                Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = lcText("Back", "返回"))
            }
            Image(painterResource(R.drawable.launch_circle_logo), contentDescription = null, modifier = Modifier.size(36.dp).clip(RoundedCornerShape(8.dp)))
            Spacer(Modifier.width(8.dp))
            Text("Launch Circle", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f), maxLines = 1)
            TextButton(onClick = { guide = true }, modifier = Modifier.heightIn(min = 48.dp)) { Text(lcText("Guide", "新手指南")) }
        }
    }
    if (guide) androidx.compose.ui.window.Dialog(
        onDismissRequest = { closeGuide(false) },
        properties = androidx.compose.ui.window.DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false),
    ) {
        val titles = listOf(lcText("Welcome to mutual testing", "先了解互测怎么进行"), lcText("Add your own app", "添加自己的 App"), lcText("Allow testers on Google Play", "开放 Google Play 测试权限"), lcText("Join your matched group", "加入自动匹配的互测小组"), lcText("Install and test another app", "安装并测试其他成员的 App"), lcText("Feedback and your next visit", "提交反馈与后续操作"))
        val destinations = listOf(lcText("Home → App Groups", "首页 → 互测小组"), lcText("My Launch → Add my app", "我的发布 → 添加我的 App"), lcText("After saving → Set up test access", "保存 App 后 → 设置测试访问"), lcText("Home → Open my group", "首页 → 打开我的小组"), lcText("Tests → Select an available task", "我的测试 → 选择可操作的任务"), lcText("Tests / My Launch", "我的测试／我的发布"))
        val instructions = listOf(
            listOf(lcText("You contribute real tests for other developers; group members can test your app in return.", "你为其他开发者实际测试，他们也可以测试你的 App。双方不需要认识，也不需要交换邀请码。"), lcText("Add your app, configure Play access, then join your automatically matched group. Google Play enrollment and installation are separate steps.", "先添加自己的 App、配置 Play 测试访问，再加入自动匹配的小组。加入互测小组不等于已经在 Google Play 加入测试或安装。"), lcText("Home shows groups and apps; Tests shows your tasks; My Launch shows your app's setup and feedback; Account contains your profile and settings.", "首页查看小组与应用；我的测试处理任务；我的发布查看自己的应用配置与反馈；账号管理个人设置。")),
            listOf(lcText("Copy your app's store or closed-testing link from Google Play. Paste it into the first field; the package is detected automatically.", "从 Google Play 复制自己 App 的商店链接或闭测链接，粘贴到第一栏，系统自动识别包名。"), lcText("Enter the app name and 2–4 concrete test steps, for example: import a sample file → preview the result → export and check the output.", "填写应用名称，以及 2–4 条具体测试步骤，例如：导入示例文件 → 预览结果 → 导出并检查文件。"), lcText("The icon and custom Google Group are optional. Save & set up test access becomes available when the required fields are valid. No Developer Account ID is required.", "图标和自定义 Google 群组为可选项。必填内容有效后，底部“保存并设置测试访问”才可点击。不用输入 Developer Account ID。")),
            listOf(lcText("Copy the Google Group email displayed on the setup page.", "复制配置页面上显示的 Google 群组邮箱。"), lcText("In your app's Play Console: Closed testing → your track → Testers → Google Groups. Add the copied email and save. Make sure the test release is available.", "在自己 App 的 Play Console：封闭测试 → 对应轨道 → 测试者 → Google 群组，添加复制的邮箱并保存，并确保测试版本已开放。"), lcText("Return to Launch Circle and confirm only after the setup is actually complete. If ownership verification fails, provide your Play link to the administrator for review.", "真正完成后再回 Launch Circle 确认。若应用所有权验证失败，把 Play 链接交给管理员审核。")),
            listOf(lcText("After test access is configured, the platform matches your app to a group. Open your group from Home and review its apps.", "测试访问配置完成后，平台自动匹配小组。在首页打开自己的小组，查看组内 App。"), lcText("Choose Join group and test its apps. This accepts tasks for current and future group members, up to 14 other developers.", "点击“加入小组并测试组内 App”，即同意测试当前和后续加入的成员应用，最多另外 14 位开发者。"), lcText("Each group has 15 developer slots. Full groups stop matching; leaving releases a slot. A forming group does not yet mean you have 12 testers.", "每组最多 15 个开发者席位，满员后停止匹配，有人退出后释放席位。小组组建中不代表已经获得 12 名测试者。")),
            listOf(lcText("Open Tests and choose an unfinished task. Read the app's instructions before installing.", "进入“我的测试”，选择未完成任务，先阅读这个 App 的操作要求。"), lcText("If required, join the displayed Google Group, then open the Play test link and opt in. Use the same Google account for the group, test enrollment and Play Store.", "按页面要求加入对应 Google 群组，再打开 Play 测试链接并加入测试。群组、测试加入页面和 Play 商店必须使用同一个 Google 账号。"), lcText("Install from Google Play, open the app and perform the requested steps. Confirm only actions you actually completed. If unavailable, check the selected account and test access first.", "从 Google Play 安装，打开 App 并实际完成指定步骤。只确认真正完成的动作。如果提示不可用，先检查账号与测试访问权限。")),
            listOf(lcText("Submit what you tried, what happened and any problem. Once submitted, that task is locked until a new task is due; do not repeatedly submit the same feedback.", "反馈中写清做了什么、结果如何、遇到什么问题。提交后该任务会锁定，新任务到期才重新开放，不要重复提交。"), lcText("Next time, open Tests for available tasks and My Launch for your app's feedback. Platform counts do not establish Google Play eligibility; check Play Console.", "下次打开“我的测试”处理可用任务，在“我的发布”查看自己 App 的反馈。平台人数不等于 Google Play 合格测试人数，资格以 Play Console 为准。"), lcText("Pausing retains your slot and tasks. Leaving stops mutual tasks and releases the slot, while keeping history. You can reopen this walkthrough anytime using Guide in the top right.", "暂停会保留席位和任务；退出会停止互测并释放席位，历史保留。以后随时点击右上角“新手指南”，可重新打开这套引导。"))
        )
        Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Column(Modifier.fillMaxSize().safeDrawingPadding()) {
                Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(lcText("Getting started", "新手引导"), modifier = Modifier.weight(1f), style = MaterialTheme.typography.titleLarge)
                    TextButton(onClick = { closeGuide(false) }) { Text(lcText("Continue later", "稍后继续")) }
                }
                LinearProgressIndicator(progress = { (step + 1) / 6f }, modifier = Modifier.fillMaxWidth())
                key(step) {
                    Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(24.dp), verticalArrangement = Arrangement.spacedBy(20.dp)) {
                        Text(lcText("STEP ", "第 ") + (step + 1) + lcText(" OF 6", " / 6 步"), style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
                        Text(titles[step], style = MaterialTheme.typography.headlineMedium)
                        Surface(color = MaterialTheme.colorScheme.secondaryContainer, shape = RoundedCornerShape(16.dp)) { Text(destinations[step], Modifier.fillMaxWidth().padding(16.dp), style = MaterialTheme.typography.titleMedium) }
                        val exampleImage = when (step) { 0, 3 -> R.drawable.guide_home; 1 -> R.drawable.guide_my_launch; else -> null }
                        if (exampleImage != null) {
                            Image(painterResource(exampleImage), contentDescription = lcText("Example screen. Tap to enlarge.", "操作页面示例，点击放大。"), contentScale = androidx.compose.ui.layout.ContentScale.Fit, modifier = Modifier.fillMaxWidth().height(220.dp).clip(RoundedCornerShape(16.dp)).clickable { preview = exampleImage })
                            Text(lcText("Example screen · tap to enlarge. Your apps and language may differ.", "界面示例，点击可放大。实际 App 与界面语言可能不同。"), style = MaterialTheme.typography.bodySmall)
                        }
                        if (onGuideAction != null) Button(onClick = { closeGuide(false); onGuideAction(if (step == 1) 5 else step) }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                            Text(lcText(when(step) { 1 -> "Go to My Launch"; 2 -> "Open test access setup"; 4 -> "Open my test tasks"; 5 -> "Open My Launch"; else -> "Open App Groups" }, when(step) { 1 -> "前往我的发布"; 2 -> "前往配置测试访问"; 4 -> "前往我的测试"; 5 -> "前往我的发布"; else -> "前往互测小组" }))
                        }
                        if (step == 1 || step == 2) OutlinedButton(onClick = {
                            linkFailed = runCatching { context.startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse("https://play.google.com/console")).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)) }.isFailure
                        }, modifier = Modifier.fillMaxWidth()) { Text(lcText("Open Google Play Console ↗", "打开 Google Play Console ↗")) }
                        if (linkFailed) Text(lcText("No browser available. Open play.google.com/console in your browser.", "无法打开浏览器，请访问 play.google.com/console。"), color = MaterialTheme.colorScheme.error)
                        instructions[step].forEachIndexed { index, instruction ->
                            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                Text((index + 1).toString(), color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.titleMedium)
                                Text(instruction, style = MaterialTheme.typography.bodyLarge)
                            }
                        }
                        Text(lcText("This walkthrough explains the steps; it does not complete tasks or change your app's status.", "此引导只说明操作，不会代替你完成任务或改变 App 状态。"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                Surface(tonalElevation = 3.dp) {
                    Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        OutlinedButton(onClick = { step-- }, enabled = step > 0, modifier = Modifier.weight(1f).heightIn(min = 48.dp)) { Text(lcText("Previous", "上一步")) }
                        Button(onClick = { if (step == 5) { closeGuide(true); step = 0 } else step++ }, modifier = Modifier.weight(1f).heightIn(min = 48.dp)) { Text(lcText(if (step == 5) "Finish guide" else "Next", if (step == 5) "完成引导" else "下一步")) }
                    }
                }
            }
        }
    }
    preview?.let { resource ->
        androidx.compose.ui.window.Dialog(onDismissRequest = { preview = null }, properties = androidx.compose.ui.window.DialogProperties(usePlatformDefaultWidth = false)) {
            Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                Column(Modifier.fillMaxSize().safeDrawingPadding()) {
                    Image(painterResource(resource), contentDescription = lcText("Enlarged example screen", "放大的操作页面示例"), contentScale = androidx.compose.ui.layout.ContentScale.Fit, modifier = Modifier.weight(1f).fillMaxWidth())
                    Button(onClick = { preview = null }, modifier = Modifier.fillMaxWidth().padding(16.dp)) { Text(lcText("Back to guide", "返回引导")) }
                }
            }
        }
    }

}
