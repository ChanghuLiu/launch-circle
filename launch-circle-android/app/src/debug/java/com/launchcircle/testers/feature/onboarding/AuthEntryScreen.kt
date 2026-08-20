package com.launchcircle.testers.feature.onboarding

import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusDirection
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.layout.padding
import com.launchcircle.testers.BuildConfig
import com.launchcircle.testers.core.model.TokenPair
import com.launchcircle.testers.core.model.UserProfile
import com.launchcircle.testers.core.storage.TokenStore
import kotlinx.coroutines.launch
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

private data class DevelopmentLoginRequest(val email: String, val password: String)
private data class DevelopmentUser(
    val id: String,
    val email: String,
    val display_name: String?,
    val country: String?,
)

private interface DevelopmentAuthApi {
    @POST("auth/login")
    suspend fun login(@Body body: DevelopmentLoginRequest): TokenPair

    @GET("me")
    suspend fun me(@Header("Authorization") authorization: String): DevelopmentUser
}

private class DevelopmentAuthRepository(baseUrl: String, private val tokenStore: TokenStore) {
    private val api = Retrofit.Builder()
        .baseUrl(baseUrl)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(DevelopmentAuthApi::class.java)

    suspend fun login(email: String, password: String): UserProfile {
        val tokens = api.login(DevelopmentLoginRequest(email, password))
        tokenStore.save(tokens.access_token, tokens.refresh_token)
        val user = api.me("Bearer ${tokens.access_token}")
        return UserProfile(
            id = user.id,
            login_email = user.email,
            display_name = user.display_name,
            tester_email = user.email,
            tester_email_sharing_consent = true,
            country = user.country ?: "CA",
            languages = listOf("en"),
            profile_ready = true,
        )
    }
}

@Composable
fun AuthEntryScreen(
    viewModel: AuthViewModel,
    tokenStore: TokenStore,
    apiBaseUrl: String,
    developmentAuthEnabled: Boolean,
    error: String?,
    onGoogleSignIn: () -> Unit,
) {
    if (BuildConfig.USE_DEMO_REPOSITORY) {
        LaunchedEffect(viewModel) {
            viewModel.acceptProfile(
                UserProfile(
                    id = "store-demo-user",
                    login_email = "pilot@launchcircle.app",
                    display_name = "Alex",
                    tester_email = null,
                    tester_email_sharing_consent = false,
                    country = "CA",
                    languages = listOf("en"),
                    profile_ready = true,
                ),
            )
        }
        return
    }
    if (!developmentAuthEnabled) {
        SignInScreen(onSignIn = onGoogleSignIn, error = error)
        return
    }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    val focusManager = LocalFocusManager.current
    val scope = rememberCoroutineScope()
    val repository = remember(apiBaseUrl, tokenStore) {
        DevelopmentAuthRepository(apiBaseUrl, tokenStore)
    }
    SignInScreen(
        onSignIn = onGoogleSignIn,
        error = error,
        extraContent = {
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
                keyboardActions = KeyboardActions(onDone = { focusManager.clearFocus() }),
            )
            Button(
                onClick = {
                    scope.launch {
                        runCatching { repository.login(email.trim(), password) }
                            .onSuccess(viewModel::acceptProfile)
                            .onFailure { viewModel.reportSignInError(it.message) }
                    }
                },
                enabled = email.contains("@") && password.length >= 8,
                modifier = Modifier.padding(top = 8.dp),
            ) {
                Text("Sign in to local backend")
            }
        },
    )
}
