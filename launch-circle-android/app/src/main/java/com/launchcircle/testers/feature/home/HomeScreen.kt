package com.launchcircle.testers.feature.home

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.core.model.UserProfile

@Composable
fun HomeScreen(profile: UserProfile, onLogout: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(24.dp)) {
        Text("Launch Circle", style = MaterialTheme.typography.headlineMedium)
        Text("Phase 0–1 foundation is ready.", modifier = Modifier.padding(top = 12.dp))
        Text("Signed in as ${profile.login_email}")
        Text("Tester email: ${profile.tester_email}")
        Text("Next: Phase 2 — Add My App", modifier = Modifier.padding(vertical = 20.dp))
        Button(onClick = onLogout) { Text("Sign out") }
    }
}
