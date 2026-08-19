package com.launchcircle.testers

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.launchcircle.testers.core.auth.AuthRepository
import com.launchcircle.testers.feature.onboarding.AuthViewModel

class SimpleAuthViewModelFactory(
    private val repository: AuthRepository,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(AuthViewModel::class.java)) {
            return AuthViewModel(repository) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
