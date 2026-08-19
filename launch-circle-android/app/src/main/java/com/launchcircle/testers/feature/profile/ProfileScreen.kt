package com.launchcircle.testers.feature.profile

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.core.model.UserProfile

@Composable
fun ProfileScreen(
    profile: UserProfile,
    onSave: (String?, String, List<String>, String, Boolean) -> Unit,
) {
    var displayName by remember { mutableStateOf(profile.display_name.orEmpty()) }
    var country by remember { mutableStateOf(profile.country.orEmpty()) }
    var languagesText by remember { mutableStateOf(profile.languages.joinToString(", ")) }
    var testerEmail by remember { mutableStateOf(profile.tester_email.orEmpty()) }
    var consent by remember { mutableStateOf(profile.tester_email_sharing_consent) }
    val languages = languagesText.split(',').map { it.trim().lowercase() }.filter { it.isNotEmpty() }
    val canSave = ProfileValidator.isReady(country, languages, testerEmail, consent)

    Column(Modifier.fillMaxSize().padding(24.dp)) {
        Text("Tester profile", style = MaterialTheme.typography.headlineMedium)
        Text(
            "Your tester email will be shared only with developers in your Launch Circle so they can add you to their Google Play closed test.",
            modifier = Modifier.padding(vertical = 12.dp),
        )
        OutlinedTextField(
            value = displayName,
            onValueChange = { displayName = it },
            label = { Text("Display name") },
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = country,
            onValueChange = { country = it.take(2).uppercase() },
            label = { Text("Country code (e.g. CA)") },
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = languagesText,
            onValueChange = { languagesText = it },
            label = { Text("Languages, comma separated") },
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = testerEmail,
            onValueChange = { testerEmail = it },
            label = { Text("Google Play tester email") },
            modifier = Modifier.fillMaxWidth(),
        )
        Row(Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
            Checkbox(checked = consent, onCheckedChange = { consent = it })
            Text("I agree to share this tester email with members of my Launch Circle.")
        }
        Button(
            onClick = { onSave(displayName.ifBlank { null }, country, languages, testerEmail, consent) },
            enabled = canSave,
        ) {
            Text("Save profile")
        }
    }
}
