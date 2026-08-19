package com.launchcircle.testers.feature.onboarding

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

internal enum class DeleteConfirmationState { CLOSED, OPEN }

internal object AccountDeletionUiLogic {
    fun requestConfirmation() = DeleteConfirmationState.OPEN
    fun cancelConfirmation() = DeleteConfirmationState.CLOSED
    fun confirmDeletion(onDelete: () -> Unit): DeleteConfirmationState {
        onDelete()
        return DeleteConfirmationState.CLOSED
    }
}

@Composable
fun AccountScreen(
    deleting: Boolean,
    error: String?,
    onBack: () -> Unit,
    onDeleteAccount: () -> Unit,
) {
    var confirmation by rememberSaveable { mutableStateOf(DeleteConfirmationState.CLOSED) }

    Column(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        OutlinedButton(onClick = onBack, enabled = !deleting) { Text("Back") }
        Text("Account / Settings", style = MaterialTheme.typography.headlineMedium)
        Text(
            "Manage your Launch Circle account. This does not change your Google account or Google Play apps.",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Button(
            onClick = { confirmation = AccountDeletionUiLogic.requestConfirmation() },
            enabled = !deleting,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(if (deleting) "Deleting account…" else "Delete account") }
    }

    if (confirmation == DeleteConfirmationState.OPEN) {
        AlertDialog(
            onDismissRequest = {
                if (!deleting) confirmation = AccountDeletionUiLogic.cancelConfirmation()
            },
            title = { Text("Permanently delete account?") },
            text = {
                Text(
                    "Your Launch Circle account and associated Launch Circle data will be permanently removed. " +
                        "This does not delete your Google account or remove apps from Google Play.",
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        confirmation = AccountDeletionUiLogic.cancelConfirmation()
                        AccountDeletionUiLogic.confirmDeletion(onDeleteAccount)
                    },
                    enabled = !deleting,
                ) { Text("Delete permanently") }
            },
            dismissButton = {
                TextButton(
                    onClick = { confirmation = AccountDeletionUiLogic.cancelConfirmation() },
                    enabled = !deleting,
                ) { Text("Cancel") }
            },
        )
    }
}
