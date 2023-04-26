/*
 * Copyright 2023 Blocker
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.merxury.blocker.tool

import com.merxury.blocker.tool.model.ExodusList
import com.merxury.blocker.tool.model.ExodusModel
import com.merxury.blocker.tool.model.GeneralRule
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.*
import java.io.File
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse

private const val EXODUS_RUlE = "https://reports.exodus-privacy.eu.org/api/trackers"

private val json = Json { prettyPrint = true }

fun main() {
    // Get original JSON response
    val client = HttpClient.newBuilder().build()

    val exodusRequest = HttpRequest.newBuilder()
        .uri(URI.create(EXODUS_RUlE))
        .build()
    val exodusResponse = client.send(exodusRequest, HttpResponse.BodyHandlers.ofString())
    val exodusRuleContent = exodusResponse.body()

    // Convert to List of objects
    val blockerRules: List<GeneralRule> = Json.decodeFromString(
        File("general-without-exodus.json").readText()
    )
    val exodusElement = Json.parseToJsonElement(exodusRuleContent)
    val exodusList = mutableListOf<ExodusModel>()
    val trackers = exodusElement.jsonObject["trackers"]
    trackers?.jsonObject?.forEach { (_, value) ->
        val model = json.decodeFromJsonElement<ExodusModel>(value)
        println(model)
        exodusList.add(model)
    }
    val excludedName = arrayOf(
        "Pangle",
        "Supersonic Ads",
        "Sensors Analytics",
        "Bugly",
        "JiGuang Aurora Mobile JPush",
        "Baidu Mobile Ads",
        "Facebook Ads",
        "Amazon Advertisement",
        "Google AdMob",
        "Unity3d Ads",
        "Twitter MoPub"
    )

    // Convert to final JSON
    val result = blockerRules.toMutableList()
    exodusList.forEach {
        if (it.name in excludedName) {
            return@forEach
        }
        val generalRule = it.toGeneralRule(result.size)
        result.add(generalRule)
    }
    val finalJson = json.encodeToString(result)

    // Write to file
    val file = File("general.json")
    file.writeText(finalJson)
}

