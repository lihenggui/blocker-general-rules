package com.merxury.blocker

import java.io.File

class Main {
    fun main() {
        val workingFile = File("").absoluteFile
            .parentFile
            .resolve("zh-cn")
        println("Working path ${workingFile.absolutePath}, exists = ${workingFile.exists()}")
    }
}