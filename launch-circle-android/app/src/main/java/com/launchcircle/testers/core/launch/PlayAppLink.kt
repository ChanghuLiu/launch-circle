package com.launchcircle.testers.core.launch

import java.net.URI
import java.net.URLDecoder

object PlayAppLink {
    private val packagePattern = Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$")

    data class ClosedTestingLink(val packageName: String, val optInUrl: String)

    fun packageName(input: String): String? {
        val value = input.trim()
        if (packagePattern.matches(value)) return value
        return parseClosedTestingLink(value)?.packageName
    }

    fun parseClosedTestingLink(input: String): ClosedTestingLink? = runCatching {
        val uri = URI(input.trim())
        if (uri.scheme != "https" || !uri.host.equals("play.google.com", ignoreCase = true) ||
            uri.userInfo != null || uri.port !in listOf(-1, 443)
        ) return null

        val path = uri.path.removeSuffix("/")
        val idValues = uri.rawQuery.orEmpty()
            .split('&')
            .filter { it.isNotEmpty() }
            .mapNotNull { part ->
                val pair = part.split('=', limit = 2)
                val key = URLDecoder.decode(pair.first(), "UTF-8")
                if (key != "id") null else URLDecoder.decode(pair.getOrElse(1) { "" }, "UTF-8")
            }
        val candidate = when {
            path.startsWith("/apps/testing/") -> path.removePrefix("/apps/testing/")
            path == "/store/apps/details" && idValues.size == 1 -> idValues.single()
            else -> return null
        }
        if (!packagePattern.matches(candidate)) return null
        if (path.startsWith("/apps/testing/") && idValues.isNotEmpty() &&
            (idValues.size != 1 || idValues.single() != candidate)
        ) return null

        ClosedTestingLink(candidate, testUrl(candidate))
    }.getOrNull()

    fun testUrl(packageName: String) = "https://play.google.com/apps/testing/$packageName"
}
