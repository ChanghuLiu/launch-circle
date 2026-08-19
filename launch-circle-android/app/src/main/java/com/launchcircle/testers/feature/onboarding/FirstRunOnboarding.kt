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
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.R

data class OnboardingPage(val title: String, val body: String)

object PilotOnboarding {
    val pages = listOf(
        OnboardingPage(
            "Need 12 testers for Google Play?",
            "Launch Circle connects Android developers who help test each other’s apps.",
        ),
        OnboardingPage(
            "One group. Ongoing access.",
            "Join the shared Google Group once, then participate in multiple developer testing cycles.",
        ),
        OnboardingPage(
            "Test others. Get tested.",
            "Complete a few meaningful test missions and build a reliable developer testing network.",
        ),
    )
}

@Composable
fun FirstRunOnboarding(onComplete: () -> Unit) {
    var page by rememberSaveable { mutableIntStateOf(0) }
    val content = PilotOnboarding.pages[page]
    Column(
        Modifier.fillMaxSize().padding(28.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Image(
            painter = painterResource(R.drawable.launch_circle_logo),
            contentDescription = "Launch Circle logo",
            modifier = Modifier.size(104.dp),
        )
        Spacer(Modifier.height(16.dp))
        Text(
            "Launch Circle",
            style = MaterialTheme.typography.titleLarge,
            color = MaterialTheme.colorScheme.primary,
        )
        Spacer(Modifier.height(28.dp))
        Text(
            content.title,
            style = MaterialTheme.typography.displaySmall,
            fontWeight = FontWeight.Bold,
        )
        Text(
            content.body,
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(top = 18.dp),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(36.dp))
        Text((page + 1).toString() + " of " + PilotOnboarding.pages.size)
        Button(
            onClick = {
                if (page == PilotOnboarding.pages.lastIndex) onComplete() else page += 1
            },
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
        ) {
            Text(if (page == PilotOnboarding.pages.lastIndex) "Get Started" else "Continue")
        }
    }
}
