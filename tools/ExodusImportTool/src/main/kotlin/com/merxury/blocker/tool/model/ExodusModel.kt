package com.merxury.blocker.tool.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ExodusModel(
    val id: String,
    val name: String,
    @SerialName("code_signature")
    val codeSignature : String,
    @SerialName("network_signature")
    val networkSignature: String,
    val website: String,
    val category: List<String>,
    @SerialName("is_in_exodus")
    val isInExodus: Boolean,
    val documentation: List<String>,
) {
    fun toGeneralRule(id: Int): GeneralRule {
        return GeneralRule(
            id = id,
            name = name,
            company = website,
            searchKeyword = codeSignature.split("|")
                .filter { it.isNotBlank() }
                .map { it.trim() },
            contributors = listOf("Exodus Tracker Investigation Platform"),
        )
    }
}