package com.launchcircle.testers.feature.onboarding

import androidx.compose.runtime.Composable
import com.launchcircle.testers.core.storage.TokenStore

@Suppress("UNUSED_PARAMETER")
@Composable
fun AuthEntryScreen(
    viewModel: AuthViewModel,
    tokenStore: TokenStore,
    apiBaseUrl: String,
    developmentAuthEnabled: Boolean,
    error: String?,
    onGoogleSignIn: () -> Unit,
) {
    SignInScreen(onSignIn = onGoogleSignIn, error = error)
}
