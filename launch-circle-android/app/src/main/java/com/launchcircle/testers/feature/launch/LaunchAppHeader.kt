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
fun LaunchAppHeader(onBack: (() -> Unit)? = null, guideAccountId: String? = null, onGuideAction: ((Int) -> Unit)? = null, onAccountAction: (() -> Unit)? = null, guideStartSignal: Int = 0, testerAccess: (@Composable () -> Unit)? = null) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val prefs = remember(context) { context.getSharedPreferences("launch_circle_guide", android.content.Context.MODE_PRIVATE) }
    val key = "guide_v4_" + (guideAccountId ?: "guest")
    var guide by rememberSaveable(key) { mutableStateOf(guideAccountId != null && !prefs.getBoolean(key + "_introduced", false)) }
    var step by rememberSaveable(key) { mutableIntStateOf(prefs.getInt(key + "_step", 0).coerceIn(0, 5)) }
    var preview by remember { mutableStateOf<Int?>(null) }
    var linkFailed by remember { mutableStateOf(false) }
    var details by remember { mutableStateOf(false) }
    LaunchedEffect(step) { details = false }
    LaunchedEffect(guideStartSignal) { if (guideStartSignal > 0) { step = 0; guide = true } }
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
            if (onAccountAction != null) TextButton(onClick = onAccountAction, modifier = Modifier.heightIn(min = 48.dp)) { Text(lcText("Account", "账号")) }
            TextButton(onClick = { step = 0; guide = true }, modifier = Modifier.heightIn(min = 48.dp)) { Text(lcText("Guide", "新手指南")) }
        }
    }
    if (guide) androidx.compose.ui.window.Dialog(
        onDismissRequest = { closeGuide(false) },
        properties = androidx.compose.ui.window.DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false),
    ) {
        val titles = listOf(lcText("Join the Google Group", "加入 Google 测试群组"), lcText("Add your own app", "添加自己的 App"), lcText("Set up Play access", "配置 Play 测试访问"), lcText("App Groups are separate", "互测小组是独立功能"), lcText("Install and test another app", "安装并测试其他成员的 App"), lcText("Feedback and your next visit", "提交反馈与后续操作"))
        val destinations = listOf("launch-circle-12-testers@googlegroups.com", lcText("My Launch → Add my app", "我的发布 → 添加我的 App"), lcText("After saving → Set up test access", "保存 App 后 → 设置测试访问"), lcText("Home → App Groups (optional)", "首页 → 互测小组（可选）"), lcText("Tests → Select an available task", "我的测试 → 选择可操作的任务"), lcText("Tests / My Launch", "我的测试／我的发布"))
        val instructions = listOf(
            listOf(lcText("Before testing, join launch-circle-12-testers@googlegroups.com with the Google account you use in Play Store.", "开始测试前，请用 Play 商店使用的 Google 账号加入 launch-circle-12-testers@googlegroups.com。"), lcText("Open the group, choose Join group and complete the request. If approval is pending, wait until you are a member before confirming.", "打开群组，选择加入并完成操作。如果申请待批准，请成为正式成员后再确认。"), lcText("Then join each app's Play test separately. App Groups inside Launch Circle organize tasks; joining one does not join the Google Group.", "之后仍需逐个 App 加入 Play 闭测。Launch Circle 的 App Groups 只组织互测任务，加入小组不会加入 Google 群组。")),
            listOf(lcText("Copy your app's store or closed-testing link from Google Play. Paste it into the first field; the package is detected automatically.", "从 Google Play 复制自己 App 的商店链接或闭测链接，粘贴到第一栏，系统自动识别包名。"), lcText("Enter the app name and 2–4 concrete test steps, for example: import a sample file → preview the result → export and check the output.", "填写应用名称，以及 2–4 条具体测试步骤，例如：导入示例文件 → 预览结果 → 导出并检查文件。"), lcText("Add a PNG or JPEG app icon, a Play link or package, your app name, and 2–4 concrete test steps. After saving, Launch Circle guides you through tester access. Save becomes available when the required details are valid.", "添加 PNG 或 JPEG 应用图标、Play 链接或包名、应用名称和 2–4 条具体测试步骤。保存后，Launch Circle 会引导你配置测试访问。必填信息有效后即可保存。")),
            listOf(lcText("Copy the shared Google Group email shown in My Launch. You add this email to every Launch Circle app; testers use the separate invite link to join the group.", "复制“我的发布”显示的共用 Google 群组邮箱。每个 Launch Circle App 都要添加此邮箱；测试者通过另一个邀请链接加入群组。"), lcText("In Play Console, select this app → Test and release → Testing → Closed testing → Manage track → Testers. Select Google Groups, add the copied email, then Save changes.", "在 Play Console 中选择此 App → 测试和发布 → 测试 → 封闭测试 → 管理测试轨道 → 测试者。选择 Google 群组，添加复制的邮箱，然后保存更改。"), lcText("Make sure this app has an available closed-test release. Return to Launch Circle and confirm only after the group is saved for this app. Repeat these steps for each app.", "确认此 App 已有可用的封闭测试版本。为此 App 保存群组后，再回 Launch Circle 确认。每个 App 都要重复这些步骤。")),
            listOf(lcText("After Play access is confirmed, your app appears on Home. Internal App Groups are separate and optional; they organize Launch Circle mutual-test tasks and do not affect Google Play access.", "确认 Play 测试访问后，你的 App 会显示在首页。Launch Circle 内部互测小组是独立的可选功能，用于组织互测任务，不影响 Google Play 访问权限。"), lcText("Browse App Groups and join one if you want to take part in Launch Circle task matching. Google Play testing still uses the same shared tester Google Group and a separate opt-in for each app.", "如需参与 Launch Circle 互测任务，可浏览并加入一个互测小组。Google Play 测试仍使用同一个共用测试群组，并且每个 App 都要单独加入测试。"), lcText("App Groups organize Launch Circle tasks; they are not Google Groups and do not count as Google Play testers.", "互测小组只组织 Launch Circle 任务；它不是 Google 群组，也不代表 Google Play 测试者人数。")),
            listOf(lcText("Open Tests and choose an unfinished task. Read the app's instructions before installing.", "进入“我的测试”，选择未完成任务，先阅读这个 App 的操作要求。"), lcText("First complete the shared Google Group step in Tests. Then open this app’s Play test link and opt in. Use the same Google account for the group, test enrollment and Play Store.", "先在“我的测试”完成共享 Google 群组步骤，再打开这个 App 的 Play 测试链接并加入测试。群组、测试加入页面和 Play 商店必须使用同一个 Google 账号。"), lcText("Install from Google Play, open the app and perform the requested steps. Confirm only actions you actually completed. If unavailable, check the selected account and test access first.", "从 Google Play 安装，打开 App 并实际完成指定步骤。只确认真正完成的动作。如果提示不可用，先检查账号与测试访问权限。")),
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
                    Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Text(lcText("STEP ", "第 ") + (step + 1) + lcText(" OF 6", " / 6 步"), style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
                        Text(titles[step], style = MaterialTheme.typography.headlineSmall)
                        Surface(color = MaterialTheme.colorScheme.secondaryContainer, shape = RoundedCornerShape(16.dp)) { Text(destinations[step], Modifier.fillMaxWidth().padding(12.dp), style = MaterialTheme.typography.bodyMedium) }
                        val screenshots = listOf(R.drawable.guide_group_access, R.drawable.guide_add_app, R.drawable.guide_test_access, R.drawable.guide_group_apps, R.drawable.guide_play_install, R.drawable.guide_tests)
                        val captions = listOf(lcText("Launch Circle · group access", "Launch Circle · 群组访问"), lcText("Launch Circle · add app", "Launch Circle · 添加 App"), lcText("Launch Circle · Play tester access", "Launch Circle · Play 测试访问"), lcText("Launch Circle · group apps", "Launch Circle · 小组应用"), lcText("Google Play · install or open", "Google Play · 安装或打开"), lcText("Launch Circle · test tasks", "Launch Circle · 测试任务"))
                        val summaries = listOf(
                            lcText("Use your Play Store Google account. Join the Google Group, then save your confirmation in Tests. Pending approval? Wait before confirming.", "使用 Play 商店的 Google 账号加入 Google 群组，再到我的测试保存确认。申请待批准时，请等待通过后再确认。"),
                            lcText("Add your Play link, app icon and a few clear test steps.", "填写 Play 链接、应用图标和简短测试步骤。"),
                            lcText("In Play Console, add the group email under Closed testing → Testers → Google Groups. Save, publish the test release, then confirm in Launch Circle.", "在 Play Console 的封闭测试 → 测试者 → Google 群组添加此邮箱。保存并开放测试版本后，再回 Launch Circle 确认。"),
                            lcText("After Play access is confirmed, your app appears on Home. Internal App Groups are separate and optional; join one if you want Launch Circle mutual-test tasks. Each app still uses the shared Google Group and its own Play opt-in.", "确认 Play 测试访问后，App 会显示在首页。Launch Circle 内部互测小组是独立可选的；如需参与互测任务，再加入小组。每个 App 仍使用共用 Google 群组，并单独加入 Play 测试。"),
                            lcText("Open a task in Tests. Join that app’s Play test, install from Google Play and try the requested steps. Use the same Google account throughout.", "打开我的测试中的任务，先加入该 App 的 Play 测试，再从 Google Play 安装并完成要求的操作。全程使用同一个 Google 账号。"),
                            lcText("Submit honest feedback inside the task. Next time, check Tests for available tasks and My Launch for feedback about your app. No task today? Nothing to submit.", "在任务内提交真实反馈。下次到我的测试查看可用任务，到我的发布查看自己 App 的反馈。今天没有任务时，无需提交。")
                        )
                        Image(painterResource(screenshots[step]), contentDescription = captions[step] + lcText(". Tap to enlarge", "，点击放大"), contentScale = androidx.compose.ui.layout.ContentScale.Fit, modifier = Modifier.fillMaxWidth().height(listOf(104, 190, 190, 190, 170, 96)[step].dp).clip(RoundedCornerShape(16.dp)).clickable { preview = screenshots[step] })
                        Text(captions[step] + lcText(" · example · tap to enlarge", " · 示例 · 点击放大"), style = MaterialTheme.typography.bodySmall)
                        Text(summaries[step], style = MaterialTheme.typography.bodyMedium)
                        if (onGuideAction != null) Button(onClick = { closeGuide(false); onGuideAction(if (step == 0) 4 else step) }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                            Text(lcText(listOf("Set up my group access", "Open My Launch", "Open tester access setup", "Browse App Groups", "Open my test tasks", "Open My Launch")[step], listOf("配置我的群组访问", "打开我的发布", "配置测试访问", "浏览互测小组", "打开我的测试", "打开我的发布")[step]))
                        }
                        TextButton(onClick = { details = !details }) { Text(lcText(if (details) "Hide details" else "Need more help?", if (details) "收起详细说明" else "需要详细说明？")) }
                        if (details && (step == 1 || step == 2)) OutlinedButton(onClick = {
                            linkFailed = runCatching { context.startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse("https://play.google.com/console")).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)) }.isFailure
                        }, modifier = Modifier.fillMaxWidth()) { Text(lcText("Open Google Play Console ↗", "打开 Google Play Console ↗")) }
                        if (linkFailed) Text(lcText("No browser available. Open play.google.com/console in your browser.", "无法打开浏览器，请访问 play.google.com/console。"), color = MaterialTheme.colorScheme.error)
                        (if (details) instructions[step] else emptyList()).forEachIndexed { index, instruction ->
                            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                Text((index + 1).toString(), color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.titleMedium)
                                Text(instruction, style = MaterialTheme.typography.bodyLarge)
                            }
                        }
                        if (details) Text(lcText("This walkthrough explains the steps; it does not complete tasks or change your app's status.", "此引导只说明操作，不会代替你完成任务或改变 App 状态。"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
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
