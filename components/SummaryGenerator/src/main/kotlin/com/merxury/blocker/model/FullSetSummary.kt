package com.merxury.blocker.model

import kotlinx.serialization.Serializable

@Serializable
data class FullSetSummary(
    val filename: String,
    val createdTime: Long,
    val version: Int,
)
