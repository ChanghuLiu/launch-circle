package com.launchcircle.testers.core.launch

import java.net.URI
import java.net.URLDecoder

object PlayAppLink {
    private val packagePattern = Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$")
    fun packageName(input: String): String? {
        val value = input.trim()
        if (packagePattern.matches(value)) return value
        return runCatching {
            val uri = URI(value)
            if (uri.scheme != "https" || uri.host != "play.google.com" || uri.userInfo != null || uri.port !in listOf(-1, 443)) return null
            val path = uri.path.removeSuffix("/")
            val candidate = if (path.startsWith("/apps/testing/")) path.removePrefix("/apps/testing/")
                else if (path == "/store/apps/details") {
                    val ids = uri.rawQuery.orEmpty().split('&').map { it.split('=', limit = 2) }.filter { it.first() == "id" }
                    if (ids.size != 1) return null
                    URLDecoder.decode(ids.single().getOrElse(1) { "" }, "UTF-8")
                } else return null
            candidate.takeIf { packagePattern.matches(it) }
        }.getOrNull()
    }
    fun testUrl(packageName: String) = "https://play.google.com/apps/testing/$packageName"
}
