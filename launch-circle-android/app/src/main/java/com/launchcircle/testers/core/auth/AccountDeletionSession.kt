package com.launchcircle.testers.core.auth

internal suspend fun deleteAccountAndClearSession(
    deleteRemote: suspend () -> Unit,
    clearSession: () -> Unit,
) {
    deleteRemote()
    clearSession()
}
