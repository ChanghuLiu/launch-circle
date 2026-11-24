package com.launchcircle.testers

import android.os.Build
import android.os.Bundle
import java.util.UUID
import androidx.activity.ComponentActivity
import androidx.activity.enableEdgeToEdge
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.launchcircle.testers.core.auth.AuthRepository
import com.launchcircle.testers.core.auth.GoogleSignInManager
import com.launchcircle.testers.core.model.DeviceUpdateRequest
import com.launchcircle.testers.core.network.ApiFactory
import com.launchcircle.testers.core.storage.InstallAttributionStore
import com.launchcircle.testers.core.storage.PlayInstallAttributionReader
import com.launchcircle.testers.core.storage.TokenStore
import com.launchcircle.testers.core.launch.DemoLaunchRepository
import com.launchcircle.testers.core.launch.RealLaunchRepository
import com.launchcircle.testers.feature.launch.LaunchViewModel
import com.launchcircle.testers.feature.launch.LaunchWorkspace
import com.launchcircle.testers.feature.onboarding.AppDestination
import com.launchcircle.testers.feature.onboarding.AppFlow
import com.launchcircle.testers.feature.onboarding.AccountDeletionUiState
import com.launchcircle.testers.feature.onboarding.AuthUiState
import com.launchcircle.testers.feature.onboarding.AuthViewModel
import com.launchcircle.testers.feature.onboarding.FirstRunOnboarding
import com.launchcircle.testers.feature.onboarding.AuthEntryScreen
import com.launchcircle.testers.feature.profile.ProfileScreen
import com.launchcircle.testers.ui.theme.LaunchCircleTheme
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val versionApi by lazy { ApiFactory.create(BuildConfig.API_BASE_URL) }
    private var versionPolicy by mutableStateOf<com.launchcircle.testers.feature.launch.AndroidVersionPolicy?>(null)
    private var versionChecking by mutableStateOf(true)
    private var versionFailed by mutableStateOf(false)
    private var versionJob: kotlinx.coroutines.Job? = null

    private fun checkAppVersion() {
        versionJob?.cancel()
        versionChecking = true
        versionJob = lifecycleScope.launch {
            do {
                try {
                    val policy = kotlinx.coroutines.withTimeout(12_000) { versionApi.androidVersion() }
                    require(policy.latest_version_code > 0 && policy.latest_version_name.isNotBlank())
                    versionPolicy = policy
                    versionFailed = false
                } catch (_: kotlinx.coroutines.TimeoutCancellationException) {
                    versionFailed = true
                } catch (e: kotlinx.coroutines.CancellationException) {
                    throw e
                } catch (_: Exception) {
                    versionFailed = true
                } finally { versionChecking = false }
                kotlinx.coroutines.delay(300_000)
            } while (true)
        }
    }

    override fun onResume() {
        super.onResume()
        checkAppVersion()
    }

    override fun onPause() {
        versionJob?.cancel()
        super.onPause()
    }


    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val api = ApiFactory.create(BuildConfig.API_BASE_URL)
        val tokenStore = TokenStore(applicationContext)
        val attributionStore = InstallAttributionStore(applicationContext)
        val installAttributionReader = PlayInstallAttributionReader(this, attributionStore)
        val repository = AuthRepository(api, tokenStore) {
            installAttributionReader.fetch() ?: attributionStore.current()
        }
        val launchRepository = if (BuildConfig.USE_DEMO_REPOSITORY) {
            DemoLaunchRepository()
        } else {
            RealLaunchRepository(api, tokenStore, repository::refreshSession)
        }
        val googleSignIn = GoogleSignInManager(this, BuildConfig.GOOGLE_SERVER_CLIENT_ID)
        val installationPreferences = getSharedPreferences("launch_circle_installation", MODE_PRIVATE)
        val installationId = installationPreferences.getString("installation_id", null)
            ?: UUID.randomUUID().toString().also {
                installationPreferences.edit().putString("installation_id", it).apply()
            }
        val device = DeviceUpdateRequest(
            installation_id = installationId,
            manufacturer = Build.MANUFACTURER,
            model = Build.MODEL,
            android_api = Build.VERSION.SDK_INT,
            capabilities = emptyList(),
        )

        setContent {
            LaunchCircleTheme {
                com.launchcircle.testers.feature.launch.RequireCurrentVersion(versionPolicy, versionChecking, versionFailed, ::checkAppVersion) {
                val pilotPreferences = getSharedPreferences("launch_circle_pilot", MODE_PRIVATE)
                var onboardingComplete by rememberSaveable {
                    mutableStateOf(pilotPreferences.getBoolean("onboarding_complete", false))
                }
                if (!onboardingComplete) {
                    FirstRunOnboarding {
                        pilotPreferences.edit().putBoolean("onboarding_complete", true).apply()
                        onboardingComplete = true
                    }
                    return@RequireCurrentVersion
                }
                val viewModel: AuthViewModel = viewModel(factory = SimpleAuthViewModelFactory(repository))
                val state by viewModel.state.collectAsState()
                val accountDeletionState by viewModel.accountDeletionState.collectAsState()
                val launchViewModel: LaunchViewModel = viewModel(
                    factory = LaunchViewModelFactory(launchRepository),
                )
                AppRoot(
                    state = state,
                    accountDeletionState = accountDeletionState,
                    authViewModel = viewModel,
                    launchViewModel = launchViewModel,
                    tokenStore = tokenStore,
                    apiBaseUrl = BuildConfig.API_BASE_URL,
                    refreshSession = repository::refreshSession,
                    developmentAuthEnabled = BuildConfig.DEBUG && BuildConfig.ENABLE_DEVELOPMENT_AUTH,
                    onGoogleSignIn = {
                        lifecycleScope.launch {
                            runCatching { googleSignIn.signIn() }
                                .onSuccess { viewModel.signIn(it, device) }
                                .onFailure { viewModel.reportSignInError(it.message) }
                        }
                    },
                    onSaveProfile = viewModel::saveProfile,
                    onDeleteAccount = {
                        viewModel.deleteAccount {
                            lifecycleScope.launch { googleSignIn.clearCredentialState() }
                        }
                    },
                    onLogout = {
                        viewModel.logout()
                        lifecycleScope.launch { googleSignIn.clearCredentialState() }
                    },
                )
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
    }
}

@Composable
private fun AppRoot(
    state: AuthUiState,
    accountDeletionState: AccountDeletionUiState,
    authViewModel: AuthViewModel,
    launchViewModel: LaunchViewModel,
    tokenStore: TokenStore,
    apiBaseUrl: String,
    refreshSession: suspend () -> Boolean,
    developmentAuthEnabled: Boolean,
    onGoogleSignIn: () -> Unit,
    onSaveProfile: (String?, String, List<String>, String, Boolean) -> Unit,
    onDeleteAccount: () -> Unit,
    onLogout: () -> Unit,
) {
    when (state) {
        AuthUiState.Loading -> androidx.compose.foundation.layout.Box(
            modifier = androidx.compose.ui.Modifier.fillMaxSize(),
            contentAlignment = androidx.compose.ui.Alignment.Center,
        ) { CircularProgressIndicator() }
        AuthUiState.SignedOut -> AuthEntryScreen(
            viewModel = authViewModel,
            tokenStore = tokenStore,
            apiBaseUrl = apiBaseUrl,
            developmentAuthEnabled = developmentAuthEnabled,
            error = null,
            onGoogleSignIn = onGoogleSignIn,
        )
        is AuthUiState.Error -> AuthEntryScreen(
            viewModel = authViewModel,
            tokenStore = tokenStore,
            apiBaseUrl = apiBaseUrl,
            developmentAuthEnabled = developmentAuthEnabled,
            error = state.message,
            onGoogleSignIn = onGoogleSignIn,
        )
        is AuthUiState.SignedIn -> when (AppFlow.destination(state.profile)) {
            AppDestination.SIGN_IN -> AuthEntryScreen(
                viewModel = authViewModel,
                tokenStore = tokenStore,
                apiBaseUrl = apiBaseUrl,
                developmentAuthEnabled = developmentAuthEnabled,
                error = null,
                onGoogleSignIn = onGoogleSignIn,
            )
            AppDestination.PROFILE -> ProfileScreen(state.profile, onSaveProfile)
            AppDestination.HOME -> {
                var groupBack by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf<(() -> Unit)?>(null) }
                var poolOpen by rememberSaveable(state.profile.id) { mutableStateOf(false) }
                var poolAppId by rememberSaveable(state.profile.id) { mutableStateOf<String?>(null) }
                fun closePool() {
                    poolOpen = false
                    launchViewModel.refresh()
                }
                androidx.activity.compose.BackHandler(enabled = poolOpen) { closePool() }
                if (poolOpen) {
                    androidx.compose.foundation.layout.Column(
                        androidx.compose.ui.Modifier.fillMaxSize().navigationBarsPadding()
                    ) {
                        com.launchcircle.testers.feature.launch.LaunchAppHeader(onBack = { closePool() }, onGuideAction = { closePool(); launchViewModel.openGuideDestination(it, state.profile.login_email.equals("liuchanghu2018@gmail.com", ignoreCase = true)) })
                        com.launchcircle.testers.feature.launch.SharedPoolScreen(apiBaseUrl, tokenStore, refreshSession, ownerAppId = poolAppId)
                    }
                } else LaunchWorkspace(
                    profile = state.profile,
                    viewModel = launchViewModel,
                    deletionInProgress = accountDeletionState is AccountDeletionUiState.Deleting,
                    deletionError = (accountDeletionState as? AccountDeletionUiState.Error)?.message,
                    onDeleteAccount = onDeleteAccount,
                    onLogout = onLogout,
                    onSharedPool = { poolAppId = null; poolOpen = true },
                    onViewMyGroup = { appId -> poolAppId = appId; poolOpen = true },
                    homeBack = groupBack,
                    communityHome = {
                        com.launchcircle.testers.feature.launch.SharedPoolScreen(
                            apiBaseUrl, tokenStore, refreshSession, home = true,
                            onAdd = launchViewModel::showAddApp,
                            onTests = launchViewModel::showToday,
                            onLaunch = launchViewModel::showHome,
                            onBackChange = { groupBack = it },
                        )
                    },
                )
            }
        }
    }
}
