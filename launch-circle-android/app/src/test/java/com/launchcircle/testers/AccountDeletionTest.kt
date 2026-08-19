package com.launchcircle.testers

import com.launchcircle.testers.core.auth.deleteAccountAndClearSession
import com.launchcircle.testers.feature.onboarding.AccountDeletionUiLogic
import com.launchcircle.testers.feature.onboarding.DeleteConfirmationState
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AccountDeletionTest {
    @Test
    fun deletionRequiresExplicitConfirmation() {
        var deleteCalls = 0
        val requested = AccountDeletionUiLogic.requestConfirmation()
        assertEquals(DeleteConfirmationState.OPEN, requested)

        val confirmed = AccountDeletionUiLogic.confirmDeletion { deleteCalls += 1 }
        assertEquals(DeleteConfirmationState.CLOSED, confirmed)
        assertEquals(1, deleteCalls)
    }

    @Test
    fun cancellationDoesNotDeleteAccount() {
        var deleteCalled = false
        val state = AccountDeletionUiLogic.cancelConfirmation()

        assertEquals(DeleteConfirmationState.CLOSED, state)
        assertFalse(deleteCalled)
    }

    @Test
    fun successfulDeletionClearsSession() = runBlocking {
        var remoteCalled = false
        var sessionCleared = false

        deleteAccountAndClearSession(
            deleteRemote = { remoteCalled = true },
            clearSession = { sessionCleared = true },
        )

        assertTrue(remoteCalled)
        assertTrue(sessionCleared)
    }

    @Test
    fun failedDeletionKeepsSession() = runBlocking {
        var sessionCleared = false

        val result = runCatching {
            deleteAccountAndClearSession(
                deleteRemote = { error("Backend unavailable") },
                clearSession = { sessionCleared = true },
            )
        }

        assertTrue(result.isFailure)
        assertFalse(sessionCleared)
    }
}
