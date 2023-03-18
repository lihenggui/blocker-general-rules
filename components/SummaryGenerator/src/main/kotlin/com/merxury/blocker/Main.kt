package com.merxury.blocker

import com.merxury.blocker.model.FullSetSummary
import com.merxury.blocker.model.OnlineComponentData
import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.decodeFromStream
import kotlinx.serialization.json.encodeToStream
import org.apache.commons.io.FileUtils
import org.apache.commons.io.filefilter.DirectoryFileFilter
import org.apache.commons.io.filefilter.RegexFileFilter
import java.io.File

// A helper file to generate CSV files from JSON content in different folders
const val SET_FILE_NAME = "collection.json"
const val INFO_FILE_NAME = "collectioninfo.json"

@OptIn(ExperimentalSerializationApi::class)
fun main() {
    val workingBaseFolder = File("").absoluteFile
        .parentFile
        .resolve("zh-cn")
    println("Working path ${workingBaseFolder.absolutePath}, exists = ${workingBaseFolder.exists()}")
    val collection = mutableListOf<OnlineComponentData>()
    val files = FileUtils.listFiles(
        workingBaseFolder,
        RegexFileFilter(".*\\.json"),
        DirectoryFileFilter.DIRECTORY
    )
    files.forEach { file ->
        if (file.absolutePath.endsWith(INFO_FILE_NAME)) return@forEach
        if (file.absolutePath.endsWith(SET_FILE_NAME)) return@forEach
        println("Resolving ${file.absolutePath}")
        file.inputStream().use { fis ->
            val component = Json.decodeFromStream<OnlineComponentData>(fis)
            collection.add(component)
        }
    }
    val summaryFile = workingBaseFolder.resolve(SET_FILE_NAME)
    summaryFile.outputStream().use { os ->
        Json.encodeToStream(collection, os)
    }
    // Generate version info
    val originalSetInfo = workingBaseFolder.resolve(INFO_FILE_NAME)
    val setInfo = if (originalSetInfo.exists()) {
        val content = originalSetInfo.readText()
        Json.decodeFromString(content)
    } else {
        originalSetInfo.createNewFile()
        FullSetSummary(INFO_FILE_NAME, 0, 0)
    }
    val newInfo = setInfo.copy(
        filename = SET_FILE_NAME,
        createdTime = System.currentTimeMillis(),
        version = setInfo.version + 1,
    )
    originalSetInfo.outputStream().use { os ->
        Json.encodeToStream(newInfo, os)
    }
}