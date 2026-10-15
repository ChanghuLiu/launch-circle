package com.launchcircle.testers.feature.onboarding

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.launchcircle.testers.R
import com.launchcircle.testers.core.model.UserProfile

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
    profile: UserProfile,
    deleting: Boolean,
    error: String?,
    onBack: () -> Unit,
    onDeleteAccount: () -> Unit,
) {
    var confirmation by rememberSaveable { mutableStateOf(DeleteConfirmationState.CLOSED) }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            TextButton(onClick = onBack, enabled = !deleting) { Text(stringResource(R.string.back)) }
            Text(stringResource(R.string.account_settings), style = MaterialTheme.typography.headlineLarge)
        }
        item { SettingsSection(stringResource(R.string.account)) }
        item {
            Card(
                Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
            ) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(profile.display_name ?: stringResource(R.string.launch_circle_developer), style = MaterialTheme.typography.titleLarge)
                    Text(profile.login_email, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    profile.tester_email?.takeIf { it.isNotBlank() }?.let {
                        Text(stringResource(R.string.tester_email_value, it), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
        item { SettingsSection(stringResource(R.string.preferences)) }
        item {
            Card(
                Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
            ) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SettingsValue(stringResource(R.string.theme), stringResource(R.string.follows_device_setting))
                    if (profile.languages.isNotEmpty()) {
                        SettingsValue(stringResource(R.string.languages), profile.languages.joinToString(", "))
                    }
                }
            }
        }
        item { SettingsSection(stringResource(R.string.danger_zone), destructive = true) }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    stringResource(R.string.account_delete_explanation),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                OutlinedButton(
                    onClick = { confirmation = AccountDeletionUiLogic.requestConfirmation() },
                    enabled = !deleting,
                    modifier = Modifier.fillMaxWidth(),
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.error),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                ) { Text(stringResource(if (deleting) R.string.deleting_account else R.string.delete_account)) }
            }
        }
    }

    if (confirmation == DeleteConfirmationState.OPEN) {
        AlertDialog(
            onDismissRequest = {
                if (!deleting) confirmation = AccountDeletionUiLogic.cancelConfirmation()
            },
            title = { Text(stringResource(R.string.permanently_delete_account_question)) },
            text = {
                Text(
                    stringResource(R.string.account_delete_confirmation),
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        confirmation = AccountDeletionUiLogic.cancelConfirmation()
                        AccountDeletionUiLogic.confirmDeletion(onDeleteAccount)
                    },
                    enabled = !deleting,
                    colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error),
                ) { Text(stringResource(R.string.delete_permanently)) }
            },
            dismissButton = {
                TextButton(
                    onClick = { confirmation = AccountDeletionUiLogic.cancelConfirmation() },
                    enabled = !deleting,
                ) { Text(stringResource(R.string.cancel)) }
            },
        )
    }
}

@Composable
private fun SettingsSection(text: String, destructive: Boolean = false) {
    Text(
        text,
        style = MaterialTheme.typography.labelLarge,
        color = if (destructive) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
    )
}

@Composable
private fun SettingsValue(label: String, value: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(label, style = MaterialTheme.typography.titleMedium)
        Text(value, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
