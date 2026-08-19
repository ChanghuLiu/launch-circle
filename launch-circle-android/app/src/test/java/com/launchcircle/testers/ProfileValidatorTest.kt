package com.launchcircle.testers

import com.launchcircle.testers.feature.profile.ProfileValidator
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProfileValidatorTest {
    @Test
    fun testerEmailRequiresBasicEmailShape() {
        assertTrue(ProfileValidator.isTesterEmailValid("tester@gmail.com"))
        assertFalse(ProfileValidator.isTesterEmailValid("tester"))
    }

    @Test
    fun profileRequiresConsent() {
        assertFalse(ProfileValidator.isReady("CA", listOf("en"), "tester@gmail.com", false))
        assertTrue(ProfileValidator.isReady("CA", listOf("en"), "tester@gmail.com", true))
    }
}
