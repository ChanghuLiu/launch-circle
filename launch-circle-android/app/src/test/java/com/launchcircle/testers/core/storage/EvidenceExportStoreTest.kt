package com.launchcircle.testers.core.storage

import java.io.ByteArrayOutputStream
import java.nio.file.Files
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class EvidenceExportStoreTest {
    @Test fun recreatedStoreRestoresExactLargeUnicodeReportFromSmallReference() {
        val directory = Files.createTempDirectory("evidence-export-test").toFile()
        try {
            val contents = "真实观察 CODEX_ASSISTED\n".repeat(100000)
            val reference = EvidenceExportStore(directory).stage(contents)
            assertTrue(reference.length < 80)
            val recreated = EvidenceExportStore(directory)
            val output = ByteArrayOutputStream()
            recreated.copyTo(reference, output)
            assertEquals(contents, output.toString("UTF-8"))
            recreated.discard(reference)
            assertFalse(directory.resolve(reference).exists())
        } finally { directory.deleteRecursively() }
    }

    @Test fun referenceCannotReadOutsideReportStagingDirectory() {
        val directory = Files.createTempDirectory("evidence-export-test").toFile()
        try {
            val store = EvidenceExportStore(directory)
            for (reference in listOf("../private.xml", "/private.xml", "session.pending")) {
                var rejected = false
                try { store.copyTo(reference, ByteArrayOutputStream()) }
                catch (_: IllegalArgumentException) { rejected = true }
                assertTrue(rejected)
            }
        } finally { directory.deleteRecursively() }
    }
}
