package com.launchcircle.testers.core.storage

import com.launchcircle.testers.core.model.InstallAttribution
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class InstallAttributionParserTest {
    @Test
    fun parsesAndNormalizesUtmValues() {
        assertEquals(
            InstallAttribution("newsletter", "email", "fall-launch"),
            InstallAttributionParser.parse(
                "utm_source=Newsletter&utm_medium=Email&utm_campaign=Fall%20Launch",
            ),
        )
    }

    @Test
    fun requiresAUsableSource() {
        assertNull(InstallAttributionParser.parse("utm_medium=email&utm_campaign=launch"))
        assertNull(InstallAttributionParser.parse("utm_source=%ZZ"))
    }
}
