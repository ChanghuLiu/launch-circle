package com.launchcircle.testers.core.network

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ApiCapabilitiesTest {
    private val enabled = """
        {"schema_version":1,"migration_revision":"0021_group_task_queue",
         "capabilities":{"owner_attestation":true,"app_group_selection":true}}
    """.trimIndent()

    @Test fun acceptsExplicit0021Capabilities() {
        val parsed = ApiCapabilities.parse(enabled)
        assertTrue(parsed.ownerAttestation)
        assertTrue(parsed.appGroupSelection)
    }

    @Test fun rejectsLegacyRevision() {
        val parsed = ApiCapabilities.parse(enabled.replace("0021_group_task_queue", "0019_user_activity_events"))
        assertFalse(parsed.ownerAttestation)
        assertFalse(parsed.appGroupSelection)
    }

    @Test fun rejects404AndMissingBody() {
        assertEqualsUnsupported(ApiCapabilities.fromHttpResult(successful = false, raw = enabled))
        assertEqualsUnsupported(ApiCapabilities.fromHttpResult(successful = true, raw = null))
    }

    @Test fun rejectsUnknownFieldsAndMalformedResponses() {
        listOf(
            enabled.replace("\"capabilities\":", "\"future_flag\":true,\"capabilities\":"),
            enabled.replace("\"app_group_selection\":true", "\"app_group_selection\":true,\"future_flag\":true"),
            enabled.replace("\"app_group_selection\":true", ""),
            enabled.replace("\"owner_attestation\":true", "\"owner_attestation\":\"true\""),
            enabled.replace("\"schema_version\":1", "\"schema_version\":\"1\""),
            "not-json",
            "{}",
        ).forEach { raw ->
            val parsed = ApiCapabilities.parse(raw)
            assertFalse(parsed.ownerAttestation)
            assertFalse(parsed.appGroupSelection)
        }
    }

    @Test fun rejectsPartialCapabilitySupport() {
        val partial = enabled.replace("\"app_group_selection\":true", "\"app_group_selection\":false")
        assertEqualsUnsupported(ApiCapabilities.parse(partial))
    }

    private fun assertEqualsUnsupported(actual: ApiCapabilities) {
        assertFalse(actual.ownerAttestation)
        assertFalse(actual.appGroupSelection)
    }
}
