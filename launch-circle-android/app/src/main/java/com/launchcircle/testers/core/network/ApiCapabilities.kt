package com.launchcircle.testers.core.network

import com.google.gson.JsonParser

data class ApiCapabilities(
    val ownerAttestation: Boolean = false,
    val appGroupSelection: Boolean = false,
) {
    companion object {
        val Unsupported = ApiCapabilities()

        /** Strict parsing is intentional: old/unknown APIs must stay fail-closed. */
        fun parse(raw: String): ApiCapabilities {
            return runCatching {
                val root = JsonParser.parseString(raw).asJsonObject
                require(root.keySet() == setOf("schema_version", "migration_revision", "capabilities"))
                val schemaVersion = root.get("schema_version")
                require(schemaVersion.isJsonPrimitive && schemaVersion.asJsonPrimitive.isNumber)
                require(schemaVersion.asInt == 1)
                val migrationRevision = root.get("migration_revision")
                require(migrationRevision.isJsonPrimitive && migrationRevision.asJsonPrimitive.isString)
                require(migrationRevision.asString == "0021_group_task_queue")
                val capabilities = root.getAsJsonObject("capabilities")
                require(capabilities.keySet() == setOf("owner_attestation", "app_group_selection"))
                val ownerNode = capabilities.get("owner_attestation")
                val groupsNode = capabilities.get("app_group_selection")
                require(ownerNode.isJsonPrimitive && ownerNode.asJsonPrimitive.isBoolean)
                require(groupsNode.isJsonPrimitive && groupsNode.asJsonPrimitive.isBoolean)
                val owner = ownerNode.asBoolean
                val groups = groupsNode.asBoolean
                if (owner && groups) ApiCapabilities(owner, groups) else Unsupported
            }.getOrDefault(Unsupported)
        }

        fun fromHttpResult(successful: Boolean, raw: String?): ApiCapabilities =
            if (successful && raw != null) parse(raw) else Unsupported
    }
}
