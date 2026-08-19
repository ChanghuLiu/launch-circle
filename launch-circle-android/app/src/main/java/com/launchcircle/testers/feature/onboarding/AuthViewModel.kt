package com.launchcircle.testers.feature.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.launchcircle.testers.core.auth.AuthRepository
import com.launchcircle.testers.core.model.DeviceUpdateRequest
import com.launchcircle.testers.core.model.UserProfile
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface AuthUiState {
    data object Loading : AuthUiState
    data object SignedOut : AuthUiState
    data class SignedIn(val profile: UserProfile) : AuthUiState
    data class Error(val message: String) : AuthUiState
}

class AuthViewModel(private val repository: AuthRepository) : ViewModel() {
    private val _state = MutableStateFlow<AuthUiState>(AuthUiState.Loading)
    val state: StateFlow<AuthUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            _state.value = repository.restoreSession()?.let(AuthUiState::SignedIn) ?: AuthUiState.SignedOut
        }
    }

    fun signIn(idToken: String, device: DeviceUpdateRequest) {
        viewModelScope.launch {
            _state.value = AuthUiState.Loading
            runCatching {
                val profile = repository.exchangeGoogleToken(idToken)
                repository.updateDevice(device)
                profile
            }.onSuccess { _state.value = AuthUiState.SignedIn(it) }
                .onFailure { _state.value = AuthUiState.Error(it.message ?: "Sign in failed") }
        }
    }

    fun developmentSignIn(email: String, password: String) {
        viewModelScope.launch {
            _state.value = AuthUiState.Loading
            runCatching {
                val profile = repository.developmentLogin(email, password)
                profile
            }.onSuccess { _state.value = AuthUiState.SignedIn(it) }
                .onFailure { _state.value = AuthUiState.Error(it.message ?: "Development login failed") }
        }
    }

    fun saveProfile(
        displayName: String?,
        country: String,
        languages: List<String>,
        testerEmail: String,
        consent: Boolean,
    ) {
        viewModelScope.launch {
            _state.value = AuthUiState.Loading
            runCatching {
                repository.updateProfile(displayName, country, languages)
                repository.updateTesterEmail(testerEmail, consent)
            }.onSuccess { _state.value = AuthUiState.SignedIn(it) }
                .onFailure { _state.value = AuthUiState.Error(it.message ?: "Profile update failed") }
        }
    }

    fun logout() {
        viewModelScope.launch {
            repository.logout()
            _state.value = AuthUiState.SignedOut
        }
    }
}
