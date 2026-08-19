package com.launchcircle.testers.core.auth

import android.app.Activity
import androidx.credentials.ClearCredentialStateRequest
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential

class GoogleSignInManager(
    private val activity: Activity,
    private val serverClientId: String,
) {
    private val credentialManager = CredentialManager.create(activity)

    suspend fun signIn(): String {
        check(!serverClientId.startsWith("CHANGE_ME")) {
            "googleServerClientId is not configured in gradle.properties"
        }
        val googleOption = GetSignInWithGoogleOption.Builder(serverClientId).build()
        val request = GetCredentialRequest.Builder()
            .addCredentialOption(googleOption)
            .build()
        val response = credentialManager.getCredential(activity, request)
        val credential = response.credential
        require(credential is CustomCredential) { "Unexpected credential type" }
        require(credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
            "Unexpected Google credential type"
        }
        return GoogleIdTokenCredential.createFrom(credential.data).idToken
    }

    suspend fun clearCredentialState() {
        credentialManager.clearCredentialState(ClearCredentialStateRequest())
    }
}
