package com.launchcircle.testers.core.model

import org.junit.Assert.assertEquals
import org.junit.Test

class CheckoutPricingTest {
    @Test
    fun showsLocalizedGooglePlayPricesForManagedCredit() {
        assertEquals(
            "CA$20.99 list price · CA$19.59 with your Managed credit",
            managedCheckoutPriceLabel("CA$20.99", "CA$19.59", hasCredit = true),
        )
    }

    @Test
    fun doesNotClaimCreditWhenNoCreditWasReserved() {
        assertEquals(
            "CA$20.99",
            managedCheckoutPriceLabel("CA$20.99", "CA$20.99", hasCredit = false),
        )
    }

    @Test
    fun waitsForGooglePlayPriceBeforeShowingCheckoutPrice() {
        assertEquals(
            "Loading Google Play price…",
            managedCheckoutPriceLabel(null, null, hasCredit = true),
        )
    }
}
