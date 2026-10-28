package com.launchcircle.testers.feature.onboarding

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.R
import com.launchcircle.testers.feature.launch.lcText

data class OnboardingPage(val title: Int, val body: Int)

object PilotOnboarding {
    val pages = listOf(
        OnboardingPage(
            R.string.onboarding_title_1,
            R.string.onboarding_body_1,
        ),
        OnboardingPage(
            R.string.onboarding_title_2,
            R.string.onboarding_body_2,
        ),
        OnboardingPage(
            R.string.onboarding_title_3,
            R.string.onboarding_body_3,
        ),
    )
}

@Composable
fun FirstRunOnboarding(onComplete: () -> Unit) {
    var page by rememberSaveable { mutableIntStateOf(0) }
    val content = PilotOnboarding.pages[page]
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Image(
            painter = painterResource(R.drawable.launch_circle_logo),
            contentDescription = stringResource(R.string.launch_circle_logo),
            modifier = Modifier.size(80.dp),
        )
        Spacer(Modifier.height(16.dp))
        Text(
            stringResource(R.string.launch_circle),
            style = MaterialTheme.typography.titleLarge,
            color = MaterialTheme.colorScheme.primary,
        )
        Spacer(Modifier.height(20.dp))
        Text(
            when(page) { 0 -> lcText("Test apps together", "和开发者一起互测"); 1 -> lcText("Start with your app", "从添加自己的 App 开始"); else -> stringResource(content.title) },
            style = MaterialTheme.typography.displaySmall,
            fontWeight = FontWeight.Bold,
        )
        Text(
            if (page == 1) lcText("Add your app, configure Play test access, then join your matched App Group. Each app still needs its own Play enrollment and installation.", "添加自己的 App、配置 Play 测试访问，再加入匹配的小组。每个 App 仍需分别加入 Play 测试并安装。") else stringResource(content.body),
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 12.dp),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(24.dp))
        ProductionJourney()
        Spacer(Modifier.height(24.dp))
        Text(
            stringResource(R.string.page_of_pages, page + 1, PilotOnboarding.pages.size),
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Button(
            onClick = {
                if (page == PilotOnboarding.pages.lastIndex) onComplete() else page += 1
            },
            modifier = Modifier.fillMaxWidth().padding(top = 10.dp).height(52.dp),
        ) {
            Text(stringResource(if (page == PilotOnboarding.pages.lastIndex) R.string.get_started else R.string.continue_))
        }
    }
}

@Composable
private fun ProductionJourney() {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            JourneyStep("1", lcText("Add your app", "添加自己的 App"))
            Text("↓", style = MaterialTheme.typography.titleLarge)
            JourneyStep("2", lcText("Join a group and test", "加入小组并实际测试"))
            Text("↓", style = MaterialTheme.typography.titleLarge)
            JourneyStep("3", lcText("Share useful feedback", "提交有用的反馈"))
            Text(lcText("Google Play decides production eligibility. Participation and approval are not guaranteed.", "正式发布资格由 Google Play 判定，不保证测试人数或审核通过。"), style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(top = 12.dp))
        }
    }
}

@Composable
private fun JourneyStep(value: String, label: String, modifier: Modifier = Modifier) {
    Column(modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.primary)
        Text(label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
