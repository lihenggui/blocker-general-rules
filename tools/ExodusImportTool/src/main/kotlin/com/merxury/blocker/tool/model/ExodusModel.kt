package com.merxury.blocker.tool.model

import jdk.jfr.Description
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import java.net.URI

@Serializable
data class ExodusModel(
    val id: Int,
    val name: String,
    val description: String,
    @SerialName("code_signature")
    val codeSignature : String,
    @SerialName("network_signature")
    val networkSignature: String,
    @SerialName("creation_date") val creationDate: String,
    val website: String,
    val categories: List<String>,
    val documentation: List<String>,
) {
    fun toGeneralRule(id: Int): GeneralRule {
        return GeneralRule(
            id = id,
            name = name,
            company = getNameFromDomain(website),
            description = description,
            searchKeyword = codeSignature.split("|")
                .filter { it.isNotBlank() }
                .map { it.trim() },
            contributors = listOf("Exodus Tracker Investigation Platform"),
        )
    }

    private fun getNameFromDomain(domain: String): String {
        val url = URI(domain)
        val host = url.host
        val names = host.split(".")
        return names[names.size - 2]
    }
}