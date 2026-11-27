package com.launchcircle.testers.core.launch

import org.junit.Assert.*
import org.junit.Test

class PlayAppLinkTest {
    @Test fun acceptsStoreTestAndPackageInputs() {
        for (input in listOf("https://play.google.com/store/apps/details?id=com.example.app&hl=zh", "https://play.google.com/apps/testing/com.example.app", " com.example.app ")) {
            assertEquals("com.example.app", PlayAppLink.packageName(input))
        }
        assertEquals("https://play.google.com/apps/testing/com.example.app", PlayAppLink.testUrl("com.example.app"))
    }

    @Test fun bothPlayConsoleTesterLinksNormalizeToTheWebOptInUrl() {
        val expected = PlayAppLink.ClosedTestingLink(
            packageName = "com.esim.checker",
            optInUrl = "https://play.google.com/apps/testing/com.esim.checker",
        )
        assertEquals(
            expected,
            PlayAppLink.parseClosedTestingLink("https://play.google.com/store/apps/details?id=com.esim.checker"),
        )
        assertEquals(expected, PlayAppLink.parseClosedTestingLink(expected.optInUrl))
        assertEquals(
            expected,
            PlayAppLink.parseClosedTestingLink("https://play.google.com/store/apps/details?id=com.esim.checker&hl=en"),
        )
    }

    @Test fun rejectsAmbiguousOrDeceptiveLinks() {
        for (input in listOf(
            "https://play.google.com.evil.test/store/apps/details?id=com.example.app",
            "https://play.google.com@evil.test/store/apps/details?id=com.example.app",
            "https://play.google.com.evil.test/apps/testing/com.example.app",
            "http://play.google.com/apps/testing/com.example.app",
            "https://play.google.com/other/path?id=com.example.app",
            "https://example.com/apps/testing/com.example.app",
            "https://play.google.com/store/apps/details",
            "https://play.google.com/store/apps/details?id=",
            "https://play.google.com/store/apps/details?id=com.a&id=com.b",
            "https://play.google.com/apps/testing/com.a?id=com.b",
            "https://play.google.com/apps/testing/com.a?id=com.a&id=com.a",
            "https://play.google.com/apps/testing/com.a/extra",
            "",
            "not a package",
        )) {
            assertNull(input, PlayAppLink.parseClosedTestingLink(input))
            assertNull(input, PlayAppLink.packageName(input))
        }
    }
}
