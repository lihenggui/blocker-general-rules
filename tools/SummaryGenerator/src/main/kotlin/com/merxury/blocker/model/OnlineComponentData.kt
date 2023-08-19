package com.merxury.blocker.model

import kotlinx.serialization.Serializable

@Serializable
data class OnlineComponentData(
    val simpleName: String,
    val fullName: String,
    val packageName: String,
    val icon: String? = null,
    val sdkName: String? = null,
    val description: String? = null,
    val disableEffect: String? = null,
    val author: String? = null,
    val addedVersion: String? = null,
    val recommendToBlock: Boolean = false,
)
