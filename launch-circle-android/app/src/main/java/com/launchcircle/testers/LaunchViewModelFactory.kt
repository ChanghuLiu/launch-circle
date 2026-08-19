package com.launchcircle.testers

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.launchcircle.testers.core.launch.LaunchRepository
import com.launchcircle.testers.feature.launch.LaunchViewModel

class LaunchViewModelFactory(
    private val repository: LaunchRepository,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(LaunchViewModel::class.java)) {
            return LaunchViewModel(repository) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: " + modelClass.name)
    }
}
