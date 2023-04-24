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
import com.merxury.blocker.tool.model.GeneralRule
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse

private const val BLOCKER_RULE =
    "https://raw.githubusercontent.com/lihenggui/blocker-general-rules/main/zh-cn/general.json"
private const val EXODUS_RUlE = "https://etip.exodus-privacy.eu.org/trackers/export"

private val json = Json { prettyPrint = true }

fun main() {
    // Get original JSON response
    val client = HttpClient.newBuilder().build()
    val blockerRequest = HttpRequest.newBuilder()
        .uri(URI.create(BLOCKER_RULE))
        .build()
    val blockerResponse = client.send(blockerRequest, HttpResponse.BodyHandlers.ofString())
    val blockerRuleContent = blockerResponse.body()
    println(blockerRuleContent)
    val exodusRequest = HttpRequest.newBuilder()
        .uri(URI.create(EXODUS_RUlE))
        .build()
    val exodusResponse = client.send(exodusRequest, HttpResponse.BodyHandlers.ofString())
    val exodusRuleContent = exodusResponse.body()
    println(exodusRuleContent)

    // Convert to List of objects
    val blockerRules: List<GeneralRule> = Json.decodeFromString(blockerRuleContent)
    val exodusList: ExodusList = Json.decodeFromString(exodusRuleContent)

    // Convert to final JSON
    val result = blockerRules.toMutableList()
    exodusList.trackers.forEach {
        val generalRule = it.toGeneralRule(result.size)
        result.add(generalRule)
    }
    val finalJson = json.encodeToString(result)

    // Write to file
    val file = java.io.File("general.json")
    file.writeText(finalJson)
}

