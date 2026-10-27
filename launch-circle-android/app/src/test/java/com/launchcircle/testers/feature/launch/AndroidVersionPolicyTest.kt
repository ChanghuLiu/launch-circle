package com.launchcircle.testers.feature.launch

import org.junit.Assert.*
import org.junit.Test

class AndroidVersionPolicyTest {
    @Test fun onlyAnOlderVersionIsBlocked() {
        val policy = AndroidVersionPolicy(15, "1.0.13", "", null)
        assertTrue(policy.requiresUpdate(14))
        assertFalse(policy.requiresUpdate(15))
        assertFalse(policy.requiresUpdate(16))
    }
}
