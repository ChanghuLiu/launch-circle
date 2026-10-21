package com.launchcircle.testers.core.storage

import java.io.File
import java.io.OutputStream
import java.util.UUID

/** Keep report bytes outside saved-state Bundles while a system document picker is open. */
class EvidenceExportStore(private val directory: File) {
    private fun file(id: String): File {
        require(id.matches(Regex("[a-f0-9-]{36}\\.pending"))) { "Invalid pending export reference" }
        return File(directory, id)
    }

    fun stage(contents: String): String {
        check(directory.isDirectory || directory.mkdirs()) { "Cannot prepare report storage" }
        directory.listFiles()?.filter {
            it.name.matches(Regex("[a-f0-9-]{36}\\.pending")) &&
                System.currentTimeMillis() - it.lastModified() > 86400000L
        }?.forEach { it.delete() }
        val id = UUID.randomUUID().toString() + ".pending"
        file(id).writeText(contents, Charsets.UTF_8)
        return id
    }

    fun copyTo(id: String, output: OutputStream) {
        file(id).inputStream().use { it.copyTo(output) }
    }

    fun discard(id: String) {
        file(id).delete()
    }
}
