package com.launchcircle.testers.feature.launch

import com.launchcircle.testers.core.model.AdditionalAppCheckout
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CheckoutConflictStateTest {
    @Test
    fun unavailableCheckoutDoesNotLeaveAnUnusablePurchaseEntry() {
        val pending = AdditionalAppCheckout(
            id = "historical-purchase",
            status = "PENDING",
            product_id = "additional_app_1",
        )
        val state = LaunchUiState(
            pilotSurface = PilotSurface.ADDITIONAL_APP_PAYMENT,
            pendingPayment = pending,
        )

        val result = additionalAppCheckoutUnavailable(state)

        assertEquals(PilotSurface.NONE, result.pilotSurface)
        assertNull(result.pendingPayment)
        assertEquals("Additional app checkout is unavailable. No payment was taken; existing paid entitlements are unchanged.", result.error)
    }
}
