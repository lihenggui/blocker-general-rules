package com.merxury.blocker.tool.model

import kotlinx.serialization.Serializable

@Serializable
data class ExodusList(
    val trackers: List<ExodusModel>
)