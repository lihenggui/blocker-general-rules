
rootProject.name = "SummaryGenerator"

dependencyResolutionManagement {
    versionCatalogs {
        create("libs") {
            library("kotlinx-serialization-json", "org.jetbrains.kotlinx:kotlinx-serialization-json:1.4.1")
            library("apache-common-io", "commons-io:commons-io:2.11.0")
        }
    }
}

