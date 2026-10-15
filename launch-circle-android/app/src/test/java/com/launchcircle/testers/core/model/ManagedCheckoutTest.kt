package com.launchcircle.testers.core.model

import org.junit.Assert.assertEquals
import org.junit.Test

class ManagedCheckoutTest {
    @Test
    fun formatsManagedListPriceCreditAndAmountDue() {
        assertEquals("USD 15.00", formatCheckoutAmount(1500))
        assertEquals("USD 1.00", formatCheckoutAmount(100))
        assertEquals("USD 14.00", formatCheckoutAmount(1400))
    }

    @Test
    fun formatsCurrencyReturnedByCheckout() {
        assertEquals("CAD 14.00", formatCheckoutAmount(1400, "cad"))
    }
}
