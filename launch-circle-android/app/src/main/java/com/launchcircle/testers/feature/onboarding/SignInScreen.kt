package com.launchcircle.testers.feature.onboarding

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusDirection
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.R

@Composable
fun SignInScreen(
    onSignIn: () -> Unit,
    developmentAuthEnabled: Boolean = false,
    error: String? = null,
    onDevelopmentSignIn: (String, String) -> Unit = { _, _ -> },
) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    val focusManager = LocalFocusManager.current

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Image(
            painter = painterResource(R.drawable.launch_circle_logo),
            contentDescription = "Launch Circle logo",
            modifier = Modifier.size(112.dp),
        )
        Text("Launch Circle: 12 Testers", style = MaterialTheme.typography.headlineMedium)
        Text(
            "Find testers. Complete your 14-day closed test. Prepare for production.",
            modifier = Modifier.padding(top = 12.dp, bottom = 24.dp),
        )
        Button(onClick = onSignIn) { Text("Continue with Google") }
        if (developmentAuthEnabled) {
            Text("Local acceptance login", modifier = Modifier.padding(top = 24.dp))
            OutlinedTextField(
                value = email,
                onValueChange = { email = it },
                label = { Text("Development email") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Email,
                    imeAction = ImeAction.Next,
                ),
                keyboardActions = KeyboardActions(
                    onNext = { focusManager.moveFocus(FocusDirection.Down) },
                ),
            )
            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                label = { Text("Development password") },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Password,
                    imeAction = ImeAction.Done,
                ),
                keyboardActions = KeyboardActions(
                    onDone = { focusManager.clearFocus() },
                ),
            )
            Button(
                onClick = { onDevelopmentSignIn(email.trim(), password) },
                enabled = email.contains("@") && password.length >= 8,
                modifier = Modifier.padding(top = 8.dp),
            ) {
                Text("Sign in to local backend")
            }
        }
        error?.let {
            Text(
                it,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(top = 12.dp),
            )
        }
    }
}
