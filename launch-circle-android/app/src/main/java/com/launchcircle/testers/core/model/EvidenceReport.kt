package com.launchcircle.testers.core.model

import com.google.gson.GsonBuilder
import com.google.gson.JsonParser

/** Human-readable export retains original observations and explicit source/eligibility fields. */
fun evidenceReportText(json: String): String {
    val report = JsonParser.parseString(json).asJsonObject
    val summary = report.getAsJsonObject("summary")
    return buildString {
        appendLine("Launch Circle testing evidence")
        appendLine("Generated: " + report.get("generated_at").asString)
        appendLine("App: " + summary.get("package_name").asString)
        appendLine("Google eligibility is NOT confirmed. Device runs do not add real participants.")
        appendLine("A passing linked retest verifies only the original recorded scope.")
        appendLine()
        append(GsonBuilder().setPrettyPrinting().create().toJson(report))
    }
}
