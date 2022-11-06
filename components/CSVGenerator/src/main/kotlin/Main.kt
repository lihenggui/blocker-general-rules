import com.google.gson.Gson
import com.google.gson.JsonSyntaxException
import data.InstantComponentInfo
import data.OnlineComponentData
import data.Set
import org.apache.commons.csv.CSVFormat
import org.apache.commons.io.FileUtils
import org.apache.commons.io.filefilter.DirectoryFileFilter
import org.apache.commons.io.filefilter.RegexFileFilter
import java.io.File


// A helper file to generate CSV files from JSON content in different folders
const val SET_FILE_NAME = "set.csv"
const val INFO_FILE_NAME = "setinfo.json"
fun main() {
    val workingFile = File("").absoluteFile
        .parentFile
        .resolve("zh-cn")
    println("Working path ${workingFile.absolutePath}, exists = ${workingFile.exists()}")

    // Convert JSON to CSV
    val instantComponentList = mutableListOf<InstantComponentInfo>()
    val gson = Gson()
    val files = FileUtils.listFiles(workingFile, RegexFileFilter(".*\\.json"), DirectoryFileFilter.DIRECTORY)
    files.forEach { file ->
        if (file.absolutePath.endsWith(INFO_FILE_NAME)) return@forEach
        println("Resolving ${file.absolutePath}")
        try {
            val content = file.readText()
            val componentData = gson.fromJson(content, OnlineComponentData::class.java)
            val packageName = getPackageName(workingFile, file)
            val instantComponent = InstantComponentInfo(
                packagePath = packageName,
                componentName = componentData.name.orEmpty(),
                description = componentData.description.orEmpty(),
                recommendToBlock = componentData.recommendToBlock
            )
            instantComponentList.add(instantComponent)
        } catch (e: JsonSyntaxException) {
            e.printStackTrace()
            return@forEach
        }
    }

    // Write to CSV file for better performance
    val csvFile = workingFile.resolve(SET_FILE_NAME)
    val writer = csvFile.bufferedWriter()
    CSVFormat.DEFAULT.print(writer).apply {
        printRecord("packagePath", "componentName", "description", "recommendToBlock")
        instantComponentList.forEach {
            printRecord(it.packagePath, it.componentName, it.description, it.recommendToBlock)
        }
    }
    writer.close()

    // Generate version info
    val originalSetInfo = workingFile.resolve(INFO_FILE_NAME)
    val setInfo = if (originalSetInfo.exists()) {
        val content = originalSetInfo.readText()
        gson.fromJson(content, Set::class.java)
    } else {
        Set(INFO_FILE_NAME, 0, 0)
    }
    setInfo.apply {
        filename = SET_FILE_NAME
        date = System.currentTimeMillis()
        version += 1
    }
    originalSetInfo.bufferedWriter().use {
        val content = gson.toJson(setInfo)
        it.write(content)
    }
}

private fun getPackageName(workingFile: File, file: File): String {
    val workingPath = workingFile.absolutePath
    val filePath = file.absolutePath
    return filePath.removePrefix(workingPath)
        .split("/")
        .dropLast(1)
        .filter { it.isNotEmpty() }
        .joinToString(".")
}